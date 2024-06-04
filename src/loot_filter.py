import time

import keyboard

from src.cam import Cam
from src.config.loader import IniConfigLoader
from src.config.models import HandleRaresType
from src.item.data.item_type import ItemType
from src.item.data.rarity import ItemRarity
from src.item.descr.read_descr import read_descr
from src.item.filter import Filter
from src.item.find_descr import find_descr
from src.logger import Logger
from src.ui.char_inventory import CharInventory
from src.ui.chest import Chest
from src.ui.inventory_base import InventoryBase
from src.utils.custom_mouse import mouse
from src.utils.image_operations import compare_histograms
from src.utils.misc import wait
from src.utils.window import screenshot


def check_items(inv: InventoryBase, force_refresh):
    occupied, _ = inv.get_item_slots()

    if force_refresh:
        reset_item_status(occupied, inv)
        occupied, _ = inv.get_item_slots()

    num_fav = sum(1 for slot in occupied if slot.is_fav)
    num_junk = sum(1 for slot in occupied if slot.is_junk)
    Logger.info(f"Items: {len(occupied)} (favorite: {num_fav}, junk: {num_junk}) in {inv.menu_name}")
    start_time = None
    img = None
    for item in occupied:
        if item.is_junk or item.is_fav:
            continue
        if start_time is not None:
            Logger.debug(f"Runtime (FullItemCheck): {time.time() - start_time:.2f}s")
            Logger.debug("----")
        # Find item descr
        start_time = time.time()
        found = False
        while not found:
            if time.time() - start_time > 6:
                Logger.error("Could not detect item descr. Timeout reached. Continue")
                if img is not None:
                    screenshot("failed_descr_detection", img=img)
                break
            inv.hover_item(item)
            wait(0.18)
            img = Cam().grab()
            start_detect = time.time()
            found, rarity, cropped_descr, _ = find_descr(img, item.center)
            if found:
                # To avoid getting an image that is taken while the fade-in animation of the item is showing
                found_check, _, cropped_descr_check, _ = find_descr(Cam().grab(), item.center)
                if found_check:
                    score = compare_histograms(cropped_descr, cropped_descr_check)
                    if score < 0.99:
                        found = False
                        continue
            Logger.debug(f"  Runtime (DetectItem): {time.time() - start_detect:.2f}s")
        if not found:
            continue

        start_time_read = time.time()
        # Detect contents of item descr
        item_descr = read_descr(rarity, cropped_descr, False)
        if item_descr is None:
            Logger.info("Retry item detection")
            wait(0.3)
            found, rarity, cropped_descr, _ = find_descr(Cam().grab(), item.center)
            if found:
                item_descr = read_descr(rarity, cropped_descr)
            if item_descr is None:
                continue
        Logger.debug(f"  Runtime (ReadItem): {time.time() - start_time_read:.2f}s")

        # Hardcoded filters
        if rarity == ItemRarity.Common and item_descr.item_type == ItemType.Material:
            Logger.info("Matched: Material")
            continue
        if rarity == ItemRarity.Legendary and item_descr.item_type == ItemType.Material:
            Logger.info("Matched: Extracted Aspect")
            continue
        if item_descr.item_type == ItemType.Elixir:
            Logger.info("Matched: Elixir")
            continue
        if item_descr.item_type == ItemType.TemperManual:
            Logger.info("Matched: Temper Manual")
            continue
        if rarity in [ItemRarity.Magic, ItemRarity.Common] and item_descr.item_type != ItemType.Sigil:
            keyboard.send("space")
            wait(0.13, 0.14)
            continue
        if rarity == ItemRarity.Rare and IniConfigLoader().general.handle_rares == HandleRaresType.ignore:
            Logger.info("Matched: Rare, ignore Item")
            continue
        if rarity == ItemRarity.Rare and IniConfigLoader().general.handle_rares == HandleRaresType.junk:
            keyboard.send("space")
            wait(0.13, 0.14)
            continue

        # Check if we want to keep the item
        start_filter = time.time()
        res = Filter().should_keep(item_descr)
        matched_any_affixes = len(res.matched) > 0 and len(res.matched[0].matched_affixes) > 0
        Logger.debug(f"  Runtime (Filter): {time.time() - start_filter:.2f}s")
        if not res.keep:
            keyboard.send("space")
            wait(0.13, 0.14)
        elif res.keep and (matched_any_affixes or item_descr.rarity == ItemRarity.Unique):
            Logger.info("Mark as favorite")
            keyboard.send("space")
            wait(0.17, 0.2)
            keyboard.send("space")
            wait(0.13, 0.14)


def reset_item_status(occupied, inv):
    for item_slot in occupied:
        if item_slot.is_fav:
            inv.hover_item(item_slot)
            keyboard.send("space")
        if item_slot.is_junk:
            inv.hover_item(item_slot)
            keyboard.send("space")
            wait(0.13, 0.14)
            keyboard.send("space")

    if occupied:
        mouse.move(*Cam().abs_window_to_monitor((0, 0)))


def run_loot_filter(force_refresh=False):
    mouse.move(*Cam().abs_window_to_monitor((0, 0)))
    Logger().info("Run Loot filter")
    inv = CharInventory()
    chest = Chest()

    if chest.is_open():
        for i in IniConfigLoader().general.check_chest_tabs:
            chest.switch_to_tab(i)
            wait(0.5)
            check_items(chest, force_refresh)
        mouse.move(*Cam().abs_window_to_monitor((0, 0)))
        wait(0.5)
        check_items(inv, force_refresh)
    else:
        if not inv.open():
            screenshot("inventory_not_open", img=Cam().grab())
            Logger.error("Inventory did not open up")
            return
        check_items(inv, force_refresh)
    mouse.move(*Cam().abs_window_to_monitor((0, 0)))
    Logger().info("Loot Filter done")
