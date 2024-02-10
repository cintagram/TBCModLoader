from dataclasses import field
import enum
from typing import Optional
import tbcml
import copy

from tbcml.io.csv_fields import (
    IntCSVField,
    StringCSVField,
)
from marshmallow_dataclass import dataclass


class AnimModificationType(enum.Enum):
    PARENT = 0
    ID = 1
    SPRITE = 2
    Z_ORDER = 3
    POS_X = 4
    POS_Y = 5
    PIVOT_X = 6
    PIVOT_Y = 7
    SCALE_UNIT = 8
    SCALE_X = 9
    SCALE_Y = 10
    ANGLE = 11
    OPACITY = 12
    H_FLIP = 13
    V_FLIP = 14


class AnimType(enum.Enum):
    WALK = 0
    IDLE = 1
    ATTACK = 2
    KNOCK_BACK = 3

    @staticmethod
    def from_bcu_str(string: str) -> Optional["AnimType"]:
        string = string.split("_")[1]
        string = string.split(".")[0]
        if string == "walk":
            return AnimType.WALK
        elif string == "idle":
            return AnimType.IDLE
        elif string == "attack":
            return AnimType.ATTACK
        elif string == "kb":
            return AnimType.KNOCK_BACK
        else:
            return None


@dataclass
class Rect:
    x: Optional[int] = None
    y: Optional[int] = None
    w: Optional[int] = None
    h: Optional[int] = None
    name: Optional[str] = None

    def __post_init__(self):
        self.csv__x = IntCSVField(col_index=0)
        self.csv__y = IntCSVField(col_index=1)
        self.csv__w = IntCSVField(col_index=2)
        self.csv__h = IntCSVField(col_index=3)
        self.csv__name = StringCSVField(col_index=4)

    def read_csv(self, index: int, csv: "tbcml.CSV"):
        csv.index = index
        tbcml.Modification.read_csv_fields(self, csv)

    def apply_csv(self, index: int, csv: "tbcml.CSV"):
        csv.index = index
        tbcml.Modification.apply_csv_fields(self, csv)


@dataclass
class TextureMetadata:
    head_name: Optional[str] = None
    version_code: Optional[str] = None
    img_name: Optional[str] = None
    total_rects: Optional[int] = None

    def __post_init__(self):
        self.csv__head_name = StringCSVField(col_index=0, row_index=0)
        self.csv__version_code = StringCSVField(col_index=0, row_index=1)
        self.csv__img_name = StringCSVField(col_index=0, row_index=2)
        self.csv__total_rects = IntCSVField(col_index=0, row_index=3)

    def read_csv(self, csv: "tbcml.CSV"):
        tbcml.Modification.read_csv_fields(self, csv)

    def apply_csv(self, csv: "tbcml.CSV"):
        tbcml.Modification.apply_csv_fields(self, csv)

    def set_unit_form(self, form: str):
        if self.img_name is None:
            raise ValueError("img_name is None!")
        name = self.img_name
        parts = name.split("_")
        id = parts[0]
        self.img_name = f"{id}_{form}.png"

    def set_id(self, id: str, form: str):
        self.img_name = f"{id}_{form}.png"


@dataclass
class Texture:
    metadata: TextureMetadata = field(default_factory=lambda: TextureMetadata())
    image: Optional["tbcml.BCImage"] = field(
        default_factory=lambda: tbcml.BCImage.create_empty()
    )
    rects: list[Rect] = field(default_factory=lambda: [])
    imgcut_name: str = ""

    def save_b64(self):
        if self.image is not None:
            self.image.save_b64()

    def read_csv(self, csv: "tbcml.CSV", imgcut_name: Optional[str] = None):
        if imgcut_name is not None:
            self.imgcut_name = imgcut_name
        self.rects = []
        self.metadata.read_csv(csv)
        for i in range(self.metadata.total_rects or 0):
            index = i + 4
            rect = Rect()
            rect.read_csv(index, csv)
            self.rects.append(rect)

    def apply_csv(
        self,
        csv: "tbcml.CSV",
        game_data: "tbcml.GamePacks",
        imgname_save_overwrite: Optional[str] = None,
    ):
        self.metadata.total_rects = len(self.rects)
        self.metadata.apply_csv(csv)
        for i, rect in enumerate(self.rects):
            index = i + 4
            rect.apply_csv(index, csv)

        self.apply_img(game_data, imgname_save_overwrite)

    def apply(self, game_data: "tbcml.GamePacks"):
        csv = tbcml.CSV()
        self.apply_csv(csv, game_data)
        game_data.set_csv(self.imgcut_name, csv)

    def apply_img(
        self, game_data: "tbcml.GamePacks", imgname_save_overwrite: Optional[str] = None
    ):
        if imgname_save_overwrite is not None:
            name = imgname_save_overwrite
        else:
            name = self.metadata.img_name
        if name is None:
            return None
        return game_data.set_img(name, self.image)

    def read_img(self, game_data: "tbcml.GamePacks", img_name: str):
        self.image = game_data.get_img(img_name)

    def set_id(self, id: str, form: str):
        if self.metadata.img_name is None:
            raise ValueError("metadata image name cannot be None!")
        self.metadata.set_id(id, form)
        self.imgcut_name = self.metadata.img_name.replace(".png", ".imgcut")

    def get_rect(self, id: int) -> Optional["Rect"]:
        try:
            rect = self.rects[id]
        except IndexError:
            return None
        return rect

    def get_cut(self, rect_id: int) -> Optional["tbcml.BCImage"]:
        if not self.image:
            return None

        rect = self.get_rect(rect_id)
        if rect is None:
            return None

        return self.image.get_subimage(rect)

    def get_cut_from_rect(self, rect: "tbcml.Rect") -> Optional["tbcml.BCImage"]:
        if self.image is None:
            return None
        return self.image.get_subimage(rect)

    def set_cut(self, rect_id: int, img: "tbcml.BCImage"):
        original_rect = self.get_rect(rect_id)
        if original_rect is None or self.image is None:
            return False
        if (
            original_rect.x is None
            or original_rect.y is None
            or original_rect.h is None
            or original_rect.w is None
        ):
            return False
        new_rect_new = img.get_rect(original_rect.x, original_rect.y)
        if new_rect_new.w is None or new_rect_new.h is None:
            return False
        self.rects[rect_id] = new_rect_new
        if new_rect_new.w <= original_rect.w and new_rect_new.h <= original_rect.h:
            self.image.wipe_rect(original_rect)
            self.image.paste_rect(img, new_rect_new)
            return True

        # reconstruct imgcut
        x = 0
        y = 0
        new_rects: list["tbcml.Rect"] = []
        for rect in self.rects:
            new_rect = tbcml.Rect()
            new_rect.x = x
            new_rect.y = 0
            new_rect.h = rect.h
            new_rect.w = rect.w
            new_rects.append(new_rect)
            x += new_rect.w or 0
            y = max(new_rect.h or 0, y)

        new_img = tbcml.BCImage.from_size(x, y)

        for i, (old_rect, new_rect) in enumerate(zip(self.rects, new_rects)):
            if i == rect_id:
                cut = img
            else:
                cut = self.get_cut_from_rect(old_rect)
            if cut is None:
                continue
            new_img.paste_rect(cut, new_rect)

        self.image = new_img
        self.rects = new_rects

        return True

    def read_from_game_file_names(
        self, game_data: "tbcml.GamePacks", img_name: str, imgcut_name: str
    ):
        self.read_img(game_data, img_name)
        csv = game_data.get_csv(imgcut_name)
        if csv is None:
            return
        self.read_csv(csv, imgcut_name)


@dataclass
class MamodelMetaData:
    head_name: Optional[str] = None
    version_code: Optional[str] = None
    total_parts: Optional[int] = None

    def __post_init__(self):
        self.csv__head_name = StringCSVField(col_index=0, row_index=0)
        self.csv__version_code = StringCSVField(col_index=0, row_index=1)
        self.csv__total_parts = IntCSVField(col_index=0, row_index=2)

    def read_csv(self, csv: "tbcml.CSV"):
        tbcml.Modification.read_csv_fields(self, csv)

    def apply_csv(self, csv: "tbcml.CSV"):
        tbcml.Modification.apply_csv_fields(self, csv)


@dataclass
class ModelPart:
    parent_id: Optional[int] = None
    unit_id: Optional[int] = None
    cut_id: Optional[int] = None
    z_depth: Optional[int] = None
    x: Optional[int] = None
    y: Optional[int] = None
    pivot_x: Optional[int] = None
    pivot_y: Optional[int] = None
    scale_x: Optional[int] = None
    scale_y: Optional[int] = None
    rotation: Optional[int] = None
    alpha: Optional[int] = None
    glow: Optional[int] = None
    name: Optional[str] = None

    def __post_init__(self):
        self.csv__parent_id = IntCSVField(col_index=0)
        self.csv__unit_id = IntCSVField(col_index=1)
        self.csv__cut_id = IntCSVField(col_index=2)
        self.csv__z_depth = IntCSVField(col_index=3)
        self.csv__x = IntCSVField(col_index=4)
        self.csv__y = IntCSVField(col_index=5)
        self.csv__pivot_x = IntCSVField(col_index=6)
        self.csv__pivot_y = IntCSVField(col_index=7)
        self.csv__scale_x = IntCSVField(col_index=8)
        self.csv__scale_y = IntCSVField(col_index=9)
        self.csv__rotation = IntCSVField(col_index=10)
        self.csv__alpha = IntCSVField(col_index=11)
        self.csv__glow = IntCSVField(col_index=12)
        self.csv__name = StringCSVField(col_index=13)

    def read_csv(self, index: int, csv: "tbcml.CSV"):
        csv.index = index
        tbcml.Modification.read_csv_fields(self, csv)

    def apply_csv(self, index: int, csv: "tbcml.CSV"):
        csv.index = index
        tbcml.Modification.apply_csv_fields(self, csv)

    def flip_rotation(self):
        if self.rotation is not None:
            self.rotation *= -1

    def flip_x(self, index: int):
        if index == 0 and self.scale_x is not None:
            self.scale_x *= -1
        self.flip_rotation()

    def flip_y(self, index: int):
        if index == 0 and self.scale_y is not None:
            self.scale_y *= -1
        self.flip_rotation()


@dataclass
class MamodelUnits:
    scale_unit: Optional[int] = None
    angle_unit: Optional[int] = None
    alpha_unit: Optional[int] = None

    def __post_init__(self):
        self.csv__scale_unit = IntCSVField(col_index=0)
        self.csv__angle_unit = IntCSVField(col_index=1)
        self.csv__alpha_unit = IntCSVField(col_index=2)

    def read_csv(self, index: int, csv: "tbcml.CSV"):
        csv.index = index
        tbcml.Modification.read_csv_fields(self, csv)

    def apply_csv(self, index: int, csv: "tbcml.CSV"):
        csv.index = index
        tbcml.Modification.apply_csv_fields(self, csv)


@dataclass
class MamodelInts:
    int_0: Optional[int] = None
    int_1: Optional[int] = None
    int_2: Optional[int] = None
    int_3: Optional[int] = None
    int_4: Optional[int] = None
    int_5: Optional[int] = None
    comment: Optional[str] = None

    def __post_init__(self):
        self.csv__int_0 = IntCSVField(col_index=0)
        self.csv__int_1 = IntCSVField(col_index=1)
        self.csv__int_2 = IntCSVField(col_index=2)
        self.csv__int_3 = IntCSVField(col_index=3)
        self.csv__int_4 = IntCSVField(col_index=4)
        self.csv__int_5 = IntCSVField(col_index=5)
        self.csv__comment = StringCSVField(col_index=6)

    def read_csv(self, index: int, csv: "tbcml.CSV"):
        csv.index = index
        tbcml.Modification.read_csv_fields(self, csv)

    def apply_csv(self, index: int, csv: "tbcml.CSV"):
        csv.index = index
        tbcml.Modification.apply_csv_fields(self, csv)


@dataclass
class MamodelIntsInts:
    ints: list[MamodelInts] = field(default_factory=lambda: [])
    total_ints: Optional[int] = None

    def __post_init__(self):
        self.csv__total_ints = IntCSVField(col_index=0)

    def read_csv(self, index: int, csv: "tbcml.CSV"):
        csv.index = index
        self.ints = []
        tbcml.Modification.read_csv_fields(self, csv)
        for i in range(self.total_ints or 0):
            ind = index + i + 1
            ints = MamodelInts()
            ints.read_csv(ind, csv)
            self.ints.append(ints)

    def apply_csv(self, index: int, csv: "tbcml.CSV"):
        csv.index = index
        self.total_ints = len(self.ints)
        tbcml.Modification.apply_csv_fields(self, csv)
        for i, ints in enumerate(self.ints):
            ind = index + i + 1
            ints.apply_csv(ind, csv)


@dataclass
class Mamodel:
    metadata: MamodelMetaData = field(default_factory=lambda: MamodelMetaData())
    parts: list[ModelPart] = field(default_factory=lambda: [])
    units: MamodelUnits = field(default_factory=lambda: MamodelUnits())
    ints: MamodelIntsInts = field(default_factory=lambda: MamodelIntsInts())
    mamodel_name: Optional[str] = None

    def read_csv(self, csv: "tbcml.CSV"):
        self.metadata.read_csv(csv)
        self.parts = []
        for i in range(self.metadata.total_parts or 0):
            index = i + 3
            part = ModelPart()
            part.read_csv(index, csv)
            self.parts.append(part)
        self.units.read_csv(len(self.parts) + 3, csv)
        self.ints.read_csv(len(self.parts) + 4, csv)

    def apply_csv(self, csv: "tbcml.CSV"):
        self.metadata.total_parts = len(self.parts)
        self.metadata.apply_csv(csv)
        for i, part in enumerate(self.parts):
            index = i + 3
            part.apply_csv(index, csv)

        self.units.apply_csv(len(self.parts) + 3, csv)
        self.ints.apply_csv(len(self.parts) + 4, csv)

    def set_unit_form(self, form: str):
        if self.mamodel_name is None:
            raise ValueError("Mamodel name cannot be None!")
        name = self.mamodel_name
        parts = name.split("_")
        id = parts[0]
        self.mamodel_name = f"{id}_{form}.mamodel"

    def set_id(self, id: str):
        if self.mamodel_name is None:
            raise ValueError("Mamodel name cannot be None!")
        name = self.mamodel_name
        parts = name.split("_")
        form = parts[1]
        self.mamodel_name = f"{id}_{form}"

        for part in self.parts[1:]:
            part.unit_id = int(id)

    def dup_ints(self):
        if len(self.ints.ints) == 1:
            self.ints.ints.append(self.ints.ints[0])
            self.ints.total_ints = 2


@dataclass
class KeyFrame:
    frame: Optional[int] = None
    change_in_value: Optional[int] = None
    ease_mode: Optional[int] = None
    ease_power: Optional[int] = None

    def __post_init__(self):
        self.csv__frame = IntCSVField(col_index=0)
        self.csv__change_in_value = IntCSVField(col_index=1)
        self.csv__ease_mode = IntCSVField(col_index=2)
        self.csv__ease_power = IntCSVField(col_index=3)

    def read_csv(self, index: int, csv: "tbcml.CSV"):
        csv.index = index
        tbcml.Modification.read_csv_fields(self, csv)

    def apply_csv(self, index: int, csv: "tbcml.CSV"):
        csv.index = index
        tbcml.Modification.apply_csv_fields(self, csv)


@dataclass
class MaanimMetadata:
    head_name: Optional[str] = None
    version_code: Optional[str] = None
    total_parts: Optional[int] = None

    def __post_init__(self):
        self.csv__head_name = StringCSVField(col_index=0, row_index=0)
        self.csv__version_code = StringCSVField(col_index=0, row_index=1)
        self.csv__total_parts = IntCSVField(col_index=0, row_index=2)

    def read_csv(self, csv: "tbcml.CSV"):
        tbcml.Modification.read_csv_fields(self, csv)

    def apply_csv(self, csv: "tbcml.CSV"):
        tbcml.Modification.apply_csv_fields(self, csv)


@dataclass
class KeyFrames:
    keyframes: list[KeyFrame] = field(default_factory=lambda: [])
    model_id: Optional[int] = None
    modification_type: Optional[int] = None
    loop: Optional[int] = None
    min_value: Optional[int] = None
    max_value: Optional[int] = None
    name: Optional[str] = None
    total_keyframes: Optional[int] = None

    def __post_init__(self):
        self.csv__model_id = IntCSVField(col_index=0)
        self.csv__modification_type = IntCSVField(col_index=1)
        self.csv__loop = IntCSVField(col_index=2)
        self.csv__min_value = IntCSVField(col_index=3)
        self.csv__max_value = IntCSVField(col_index=4)
        self.csv__name = StringCSVField(col_index=5)
        self.csv__total_keyframes = IntCSVField(col_index=0, row_offset=1)

    def read_csv(self, index: int, csv: "tbcml.CSV") -> int:
        csv.index = index
        tbcml.Modification.read_csv_fields(self, csv)
        self.keyframes = []
        for i in range(self.total_keyframes or 0):
            ind = index + i + 2
            keyframe = KeyFrame()
            keyframe.read_csv(ind, csv)
            self.keyframes.append(keyframe)

        return index + 2 + len(self.keyframes)

    def apply_csv(self, index: int, csv: "tbcml.CSV") -> int:
        csv.index = index
        self.total_keyframes = len(self.keyframes)
        tbcml.Modification.apply_csv_fields(self, csv)
        for i, keyframe in enumerate(self.keyframes):
            ind = index + i + 2
            keyframe.apply_csv(ind, csv)

        return index + 2 + len(self.keyframes)

    def flip(self):
        if self.modification_type != AnimModificationType.ANGLE.value:
            return
        for keyframe in self.keyframes:
            if keyframe.change_in_value is not None:
                keyframe.change_in_value = -keyframe.change_in_value


@dataclass
class UnitAnim:
    metadata: MaanimMetadata = field(default_factory=lambda: MaanimMetadata())
    parts: list[KeyFrames] = field(default_factory=lambda: [])
    name: Optional[str] = None

    def read_csv(self, csv: "tbcml.CSV"):
        self.metadata.read_csv(csv)
        index = 3
        self.parts = []
        for _ in range(self.metadata.total_parts or 0):
            part = KeyFrames()
            index = part.read_csv(index, csv)
            self.parts.append(part)

    def apply_csv(self, csv: "tbcml.CSV"):
        self.metadata.total_parts = len(self.parts)
        self.metadata.apply_csv(csv)
        index = 3
        for part in self.parts:
            index = part.apply_csv(index, csv)

    def flip(self):
        for part in self.parts:
            part.flip()

    def set_unit_form(self, form: str):
        if self.name is None:
            raise ValueError("unit anim name cannot be None!")
        name = self.name
        parts = name.split("_")
        id = parts[0]
        anim_id = parts[1][1:3]
        self.name = f"{id}_{form}{anim_id}.maanim"

    def set_id(self, id: str):
        if self.name is None:
            raise ValueError("unit anim name cannot be None!")
        parts = self.name.split("_")
        parts[0] = id
        self.name = "_".join(parts)


@dataclass
class Model(tbcml.Modification):
    texture: Texture = field(default_factory=lambda: Texture())
    anims: list[UnitAnim] = field(default_factory=lambda: [])
    mamodel: Mamodel = field(default_factory=lambda: Mamodel())

    def read_csv(
        self,
        img: Optional["tbcml.BCImage"],
        imgcut_csv: Optional["tbcml.CSV"],
        maanim_csvs: dict[str, "tbcml.CSV"],
        mamodel_csv: Optional["tbcml.CSV"],
    ):
        if imgcut_csv is not None:
            self.texture.read_csv(imgcut_csv)
        self.texture.image = img
        self.anims = []
        for name, maanim_csv in maanim_csvs.items():
            anim = UnitAnim(name=name)
            anim.read_csv(maanim_csv)
            self.anims.append(anim)

        if mamodel_csv is not None:
            self.mamodel.read_csv(mamodel_csv)

    def apply_csv(
        self,
        imgcut_csv: "tbcml.CSV",
        maanim_csvs: dict[str, "tbcml.CSV"],
        mamodel_csv: "tbcml.CSV",
        game_data: "tbcml.GamePacks",
    ):
        self.texture.apply_csv(imgcut_csv, game_data)
        for anim in self.anims:
            if anim.name is None:
                continue
            maanim_csv = maanim_csvs.get(anim.name)
            if maanim_csv is not None:
                anim.apply_csv(maanim_csv)
        self.mamodel.apply_csv(mamodel_csv)

    def read(
        self,
        game_data: "tbcml.GamePacks",
        sprite_name: str,
        imgcut_name: str,
        maanim_names: list[str],
        mamodel_name: str,
    ):
        self.texture.imgcut_name = imgcut_name
        self.texture.metadata.img_name = sprite_name

        texture_csv = game_data.get_csv(imgcut_name)

        self.mamodel.mamodel_name = mamodel_name

        mamodel_csv = game_data.get_csv(mamodel_name)

        maanim_csvs: dict[str, "tbcml.CSV"] = {}
        for maanim_name in maanim_names:
            maanim_csv = game_data.get_csv(maanim_name)
            if maanim_csv is not None:
                maanim_csvs[maanim_name] = maanim_csv

        img = game_data.get_img(sprite_name)

        self.read_csv(img, texture_csv, maanim_csvs, mamodel_csv)

    def read_files(
        self,
        sprite_path: "tbcml.Path",
        imgcut_path: "tbcml.Path",
        maanim_paths: list["tbcml.Path"],
        mamodel_path: "tbcml.Path",
    ):
        self.texture.imgcut_name = imgcut_path.basename()
        self.texture.metadata.img_name = sprite_path.basename()
        texture_csv = tbcml.CSV(imgcut_path.read())

        self.mamodel.mamodel_name = mamodel_path.basename()
        mamodel_csv = tbcml.CSV(mamodel_path.read())

        maanim_csvs: dict[str, "tbcml.CSV"] = {}
        for path in maanim_paths:
            maanim_csv = tbcml.CSV(path.read())
            maanim_csvs[path.basename()] = maanim_csv

        self.read_csv(
            tbcml.BCImage.from_file(sprite_path),
            texture_csv,
            maanim_csvs,
            mamodel_csv,
        )

    def read_data(
        self,
        sprite_name: str,
        sprite_data: "tbcml.Data",
        imgcut_name: str,
        imgcut_data: "tbcml.Data",
        maanim_names: list[str],
        maanim_datas: list["tbcml.Data"],
        mamodel_name: str,
        mamodel_data: "tbcml.Data",
    ):
        self.texture.imgcut_name = imgcut_name
        self.texture.metadata.img_name = sprite_name
        texture_csv = tbcml.CSV(imgcut_data)

        self.mamodel.mamodel_name = mamodel_name
        mamodel_csv = tbcml.CSV(mamodel_data)

        maanim_csvs: dict[str, "tbcml.CSV"] = {}
        for name, data in zip(maanim_names, maanim_datas):
            maanim_csv = tbcml.CSV(data)
            maanim_csvs[name] = maanim_csv

        self.read_csv(
            tbcml.BCImage.from_data(sprite_data),
            texture_csv,
            maanim_csvs,
            mamodel_csv,
        )

    def apply(self, game_data: "tbcml.GamePacks"):
        texture_csv = tbcml.CSV()
        self.texture.apply_csv(texture_csv, game_data)
        game_data.set_csv(self.texture.imgcut_name, texture_csv)

        mamodel_csv = tbcml.CSV()
        self.mamodel.apply_csv(mamodel_csv)
        if self.mamodel.mamodel_name is not None:
            game_data.set_csv(self.mamodel.mamodel_name, mamodel_csv)

        for maanim in self.anims:
            maanim_csv = tbcml.CSV()
            maanim.apply_csv(maanim_csv)
            if maanim.name is not None:
                game_data.set_csv(maanim.name, maanim_csv)

    def flip_x(self):
        for i, part in enumerate(self.mamodel.parts):
            part.flip_x(i)
        self.flip_anims()

    def flip_y(self):
        for i, part in enumerate(self.mamodel.parts):
            part.flip_y(i)
        self.flip_anims()

    def flip_anims(self):
        for anim in self.anims:
            anim.flip()

    def deepcopy(self) -> "Model":
        return copy.deepcopy(self)

    def set_unit_form(self, id: int, form: str):
        id_str = tbcml.PaddedInt(id, 3).to_str()
        self.texture.set_id(id_str, form)
        self.mamodel.set_unit_form(form)
        for anim in self.anims:
            anim.set_unit_form(form)

    def set_id(self, id: int, form: str):
        id_str = tbcml.PaddedInt(id, 3).to_str()
        self.texture.set_id(id_str, form)
        self.mamodel.set_id(id_str)
        for anim in self.anims:
            anim.set_id(id_str)
