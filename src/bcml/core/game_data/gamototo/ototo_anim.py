from typing import Any
import enum
from bcml.core.game_data import pack
from bcml.core import io, anim


class MainChara:
    class FilePath(enum.Enum):
        IMGCUT = "castleCustom_mainChara_001.imgcut"
        MAMODEL = "castleCustom_mainChara_001.mamodel"
        SPRITE = "castleCustom_mainChara_001.png"

        MAANIM_ACTION_L_OPEN = "castleCustom_mainChara_actionL_open.maanim"
        MAANIM_ACTION_R_OPEN = "castleCustom_mainChara_actionR_open.maanim"

        MAANIM_HAPPY = "castleCustom_mainChara_happy.maanim"

        MAANIM_RUN_L = "castleCustom_mainChara_runL.maanim"
        MAANIM_RUN_R = "castleCustom_mainChara_runR.maanim"

        MAANIM_WAIT_L = "castleCustom_mainChara_waitL.maanim"
        MAANIM_WAIT_L_OPEN = "castleCustom_mainChara_waitL_open.maanim"
        MAANIM_WAIT_R = "castleCustom_mainChara_waitR.maanim"
        MAANIM_WAIT_R_OPEN = "castleCustom_mainChara_waitR_open.maanim"

        MAANIM_WALK_L = "castleCustom_mainChara_walkL.maanim"
        MAANIM_WALK_L_OPEN = "castleCustom_mainChara_walkL_open.maanim"
        MAANIM_WALK_R = "castleCustom_mainChara_walkR.maanim"
        MAANIM_WALK_R_OPEN = "castleCustom_mainChara_walkR_open.maanim"

        @staticmethod
        def get_all_maanims() -> list["MainChara.FilePath"]:
            all_maanims: list["MainChara.FilePath"] = []
            for member in MainChara.FilePath:
                if member.value.endswith(".maanim"):
                    all_maanims.append(member)
            return all_maanims

        @staticmethod
        def get_all_maanims_names() -> list[str]:
            all_maanims: list[str] = []
            for member in MainChara.FilePath:
                if member.value.endswith(".maanim"):
                    all_maanims.append(member.value)
            return all_maanims

    def __init__(self, model: "anim.model.Model"):
        self.model = model

    def serialize(self) -> dict[str, Any]:
        return {
            "model": self.model.serialize(),
        }

    @staticmethod
    def deserialize(data: dict[str, Any]) -> "MainChara":
        return MainChara(anim.model.Model.deserialize(data["model"]))

    def to_zip(self, zip: "io.zip.Zip"):
        path = MainChara.get_zip_path()
        json_data = io.json_file.JsonFile.from_object(self.serialize()).to_data()
        zip.add_file(path.add("main_chara.json"), json_data)

    @staticmethod
    def get_zip_path() -> io.path.Path:
        return io.path.Path("gamototo").add("ototo")

    @staticmethod
    def from_zip(zip: "io.zip.Zip") -> "MainChara":
        path = MainChara.get_zip_path()
        json_data = zip.get_file(path.add("main_chara.json"))
        if json_data is None:
            return MainChara.create_empty()
        json_file = io.json_file.JsonFile.from_data(json_data)
        return MainChara.deserialize(json_file.get_json())

    @staticmethod
    def from_game_data(game_data: "pack.GamePacks") -> "MainChara":
        an = anim.model.Model.load(
            MainChara.FilePath.MAMODEL.value,
            MainChara.FilePath.IMGCUT.value,
            MainChara.FilePath.SPRITE.value,
            MainChara.FilePath.get_all_maanims_names(),
            game_data,
        )
        return MainChara(an)

    def to_game_data(self, game_data: "pack.GamePacks"):
        self.model.save(game_data)

    @staticmethod
    def create_empty() -> "MainChara":
        return MainChara(anim.model.Model.create_empty())

    def import_main_chara(self, other: "MainChara", game_data: "pack.GamePacks"):
        """_summary_

        Args:
            other (MainChara): _description_
            game_data (pack.GamePacks): The game data to check if the imported data is different from the game data. This is used to prevent overwriting the current data with base game data.
        """
        gd_chara = self.from_game_data(game_data)
        if gd_chara != other:
            self.model = other.model