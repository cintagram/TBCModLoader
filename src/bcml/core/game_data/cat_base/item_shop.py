from typing import Any, Optional
from bcml.core.game_data import pack
from bcml.core import io, anim


class Item:
    """Represents an item in the Item Shop."""

    def __init__(
        self,
        shop_id: int,
        gatya_item_id: int,
        count: int,
        price: int,
        draw_item_value: bool,
        category_name: str,
        rect_id: int,
    ):
        """Initialize a new Item.

        Args:
            shop_id (int): The index of the item in the shop.
            gatya_item_id (int): The ID of the item to sell.
            count (int): The number of items to sell.
            price (int): The price of the item in catfood.
            draw_item_value (bool): Whether to draw the player's current item count of the item.
            category_name (str): The name of the category the item belongs to. e.g "Battle Items", "XP"
            rect (int): The index in the texture of the item's icon.
        """
        self.shop_id = shop_id
        self.gatya_item_id = gatya_item_id
        self.count = count
        self.price = price
        self.draw_item_value = draw_item_value
        self.category_name = category_name
        self.rect_id = rect_id

    def serialize(self) -> dict[str, Any]:
        """Serialize the Item to a dict.

        Returns:
            dict[str, Any]: The serialized Item.
        """
        return {
            "shop_id": self.shop_id,
            "gatya_item_id": self.gatya_item_id,
            "count": self.count,
            "price": self.price,
            "draw_item_value": self.draw_item_value,
            "category_name": self.category_name,
            "rect_id": self.rect_id,
        }

    @staticmethod
    def deserialize(data: dict[str, Any]) -> "Item":
        """Deserialize an Item from a dict.

        Args:
            data (dict[str, Any]): The serialized Item.

        Returns:
            Item: The deserialized Item.
        """
        item = Item(
            data["shop_id"],
            data["gatya_item_id"],
            data["count"],
            data["price"],
            data["draw_item_value"],
            data["category_name"],
            data["rect_id"],
        )
        return item

    def __str__(self) -> str:
        """Get a string representation of the Item.

        Returns:
            str: The string representation of the Item.
        """
        return f"Item(shop_id={self.shop_id}, gatya_item_id={self.gatya_item_id}, count={self.count}, price={self.price}, draw_item_value={self.draw_item_value}, category_name={self.category_name}, rect_id={self.rect_id})"

    def __repr__(self) -> str:
        """Get a string representation of the Item.

        Returns:
            str: The string representation of the Item.
        """
        return str(self)

    def __eq__(self, other: object) -> bool:
        """Check if two Items are equal.

        Args:
            other (object): The other Item.

        Returns:
            bool: Whether the two Items are equal.
        """

        if not isinstance(other, Item):
            return False
        return (
            self.shop_id == other.shop_id
            and self.gatya_item_id == other.gatya_item_id
            and self.count == other.count
            and self.price == other.price
            and self.draw_item_value == other.draw_item_value
            and self.category_name == other.category_name
            and self.rect_id == other.rect_id
        )

    def __ne__(self, other: object) -> bool:
        """Check if two Items are not equal.

        Args:
            other (object): The other Item.

        Returns:
            bool: Whether the two Items are not equal.
        """
        return not self.__eq__(other)


class ItemShop:
    """Represents the Item Shop."""

    def __init__(self, items: dict[int, Item], tex: "anim.texture.Texture"):
        """Initialize a new ItemShop.

        Args:
            items (dict[int, Item]): The items in the shop.
            tex (anim.texture.Texture): The texture containing the icons for the items.
        """
        self.items = items
        self.tex = tex

    def serialize(self) -> dict[str, Any]:
        """Serialize the ItemShop to a dict.

        Returns:
            dict[str, Any]: The serialized ItemShop.
        """
        return {
            "items": {str(k): v.serialize() for k, v in self.items.items()},
            "tex": self.tex.serialize(),
        }

    @staticmethod
    def deserialize(data: dict[str, Any]) -> "ItemShop":
        """Deserialize an ItemShop from a dict.

        Args:
            data (dict[str, Any]): The serialized ItemShop.

        Returns:
            ItemShop: The deserialized ItemShop.
        """
        items = {int(k): Item.deserialize(v) for k, v in data["items"].items()}
        tex = anim.texture.Texture.deserialize(data["tex"])
        return ItemShop(items, tex)

    @staticmethod
    def get_file_name() -> str:
        """Get the name of the file containing the ItemShop data.

        Returns:
            str: The name of the file containing the ItemShop data.
        """
        return "itemShopData.tsv"

    @staticmethod
    def get_imgname(lang: str) -> str:
        """Get the name of the file containing the ItemShop icons.

        Args:
            cc (country_code.CountryCode): The country code of the game.

        Returns:
            str: The name of the file containing the ItemShop icons.
        """
        return f"item000_{lang}.png"

    @staticmethod
    def from_game_data(game_data: "pack.GamePacks") -> "ItemShop":
        """Get the ItemShop from the game data.

        Args:
            game_data (pack.GamePacks): The game data.

        Returns:
            ItemShop: The ItemShop.
        """
        tsv_data = game_data.find_file(ItemShop.get_file_name())
        png_name = f"item000_{game_data.localizable.get_lang()}.png"
        imgcut_name = f"item000_{game_data.localizable.get_lang()}.imgcut"
        tex = anim.texture.Texture.load(png_name, imgcut_name, game_data)
        if tsv_data is None:
            return ItemShop.create_empty()
        tsv = io.bc_csv.CSV(tsv_data.dec_data, delimeter="\t")
        items = {}
        for line in tsv.lines[1:]:
            items[line[0].to_int()] = Item(
                line[0].to_int(),
                line[1].to_int(),
                line[2].to_int(),
                line[3].to_int(),
                line[4].to_bool(),
                line[5].to_str(),
                line[6].to_int(),
            )
        return ItemShop(items, tex)

    def get_texture(self) -> "anim.texture.Texture":
        """Get the Imgcut of the ItemShop.

        Returns:
            bc_anim.Imgcut: The Imgcut of the ItemShop.
        """
        return self.tex

    def to_game_data(self, game_data: "pack.GamePacks"):
        """Write the ItemShop to the game data.

        Args:
            game_data (pack.GamePacks): The game data.
        """
        tsv_data = game_data.find_file(ItemShop.get_file_name())
        if tsv_data is None:
            return
        tsv = io.bc_csv.CSV(tsv_data.dec_data, delimeter="\t")
        remaning_items = self.items.copy()
        for i, line in enumerate(tsv.lines[1:]):
            try:
                item = self.items[line[0].to_int()]
            except KeyError:
                continue
            line[1].set(item.gatya_item_id)
            line[2].set(item.count)
            line[3].set(item.price)
            line[4].set(item.draw_item_value)
            line[5].set(item.category_name)
            line[6].set(item.rect_id)
            del remaning_items[line[0].to_int()]
            tsv.set_line(i + 1, line)

        for item in remaning_items.values():
            line: list[Any] = []
            line.append(item.shop_id)
            line.append(item.gatya_item_id)
            line.append(item.count)
            line.append(item.price)
            line.append(item.draw_item_value)
            line.append(item.category_name)
            line.append(item.rect_id)
            tsv.add_line(line)

        game_data.set_file(ItemShop.get_file_name(), tsv.to_data())
        tex = self.get_texture()
        if not tex.is_empty():
            tex.save(game_data)

    @staticmethod
    def get_json_file_path() -> "io.path.Path":
        """Get the path of the json file containing the ItemShop data.

        Returns:
            io.path.Path: The path of the json file containing the ItemShop data.
        """
        return io.path.Path("catbase").add("item_shop.json")

    def add_to_zip(self, zip_file: "io.zip.Zip"):
        """Add the ItemShop to a zip file.

        Args:
            zip_file (io.zip.Zip): The zip file.
        """
        json = io.json_file.JsonFile.from_object(self.serialize())
        zip_file.add_file(ItemShop.get_json_file_path(), json.to_data())

    @staticmethod
    def from_zip(zip: "io.zip.Zip") -> "ItemShop":
        """Create an ItemShop from a zip file.

        Args:
            zip (io.zip.Zip): The zip file.

        Returns:
            ItemShop: The ItemShop.
        """
        json_data = zip.get_file(ItemShop.get_json_file_path())
        if json_data is None:
            return ItemShop.create_empty()
        json = io.json_file.JsonFile.from_data(json_data)
        return ItemShop.deserialize(json.get_json())

    @staticmethod
    def create_empty() -> "ItemShop":
        """Create an empty ItemShop.

        Returns:
            ItemShop: The empty ItemShop.
        """
        return ItemShop({}, anim.texture.Texture.create_empty())

    def get_item(self, shop_index: int) -> Optional[Item]:
        """Get an item from the ItemShop.

        Args:
            shop_index (int): The index of the item in the ItemShop.

        Returns:
            Optional[Item]: The item.
        """
        return self.items.get(shop_index)

    def set_item(self, shop_index: int, item: Item):
        """Set an item in the ItemShop.

        Args:
            shop_index (int): The index of the item in the ItemShop.
            item (Item): The item.
        """
        item.shop_id = shop_index
        self.items[shop_index] = item

    def import_item_shop(self, other: "ItemShop", game_data: "pack.GamePacks"):
        """Import an ItemShop into this ItemShop.

        Args:
            other (ItemShop): The ItemShop to import.
            game_data (pack.GamePacks): The game data to check if the imported data is different from the game data. This is used to prevent overwriting the current data with base game data.
        """
        gd_item_shop = self.from_game_data(game_data)
        all_keys = set(self.items.keys())
        all_keys.update(other.items.keys())
        all_keys.update(gd_item_shop.items.keys())

        attrs = [
            "gatya_item_id",
            "count",
            "price",
            "draw_item_value",
            "category_name",
            "imgcut_id",
            "cut",
        ]

        for id in all_keys:
            other_item = other.get_item(id)
            if other_item is None:
                continue
            gd_item = gd_item_shop.get_item(id)
            current_item = self.get_item(id)
            if gd_item is not None:
                for attr in attrs:
                    other_value = getattr(other_item, attr)
                    gd_value = getattr(gd_item, attr)
                    if other_value != gd_value:
                        setattr(current_item, attr, other_value)
            else:
                self.set_item(id, other_item)

    def add_item(self, item: Item):
        """Add an item to the ItemShop.

        Args:
            item (Item): The item to add.
        """
        self.set_item(item.shop_id, item)

    def remove_item(self, shop_index: int):
        """Remove an item from the ItemShop.

        Args:
            shop_index (int): The index of the item in the ItemShop.
        """
        self.items.pop(shop_index)
        self.shift_items(shop_index + 1, -1)

    def shift_items(self, start_index: int, shift: int):
        """Move all items after a certain index.

        Args:
            start_index (int): The index to start shifting from.
            shift (int): The amount to shift by.
        """
        for item in self.items.values():
            if item.shop_id >= start_index:
                item.shop_id += shift
        self.items = {item.shop_id: item for item in self.items.values()}

    def insert_item(self, shop_index: int, item: Item):
        """Insert an item into the ItemShop.

        Args:
            shop_index (int): The index to insert the item at.
            item (Item): The item to insert.
        """
        self.shift_items(shop_index, 1)
        self.set_item(shop_index, item)