from PyQt5 import QtWidgets, QtCore, QtGui
from tbcml.core import locale_handler, anim, io
from tbcml.ui.ui_anim import anim_viewer, keyframe_viewer
from tbcml.ui import utils, main
from typing import Any, Callable, Optional


class AnimViewerBox(QtWidgets.QGroupBox):
    def __init__(
        self,
        model: anim.model.Model,
        parent: QtWidgets.QWidget,
        anim_id: int,
        frame_tick: Callable[..., None],
    ):
        super(AnimViewerBox, self).__init__(parent)
        self.model = model
        self.anim_id = anim_id
        self.frame_tick = frame_tick

        self.locale_manager = locale_handler.LocalManager.from_config()
        self.setup_ui()

    def setup_ui(self):
        self.setObjectName("anim_viewer_box")
        self._layout = QtWidgets.QGridLayout(self)

        self.anim_label = QtWidgets.QLabel(self)
        self.anim_label.setObjectName("anim_label")
        self.anim_label.setText(self.locale_manager.search_key("anim"))
        self._layout.addWidget(self.anim_label, 0, 0)

        self.anim_viewer = anim_viewer.AnimViewer(
            self.model,
            self,
            self.anim_id,
            False if self.anim_id == 0 else True,
        )
        self._layout.addWidget(self.anim_viewer, 1, 0)

        self._layout.setColumnStretch(0, 1)
        self._layout.setRowStretch(1, 1)

        self.anim_viewer.clock.connect(self.frame_tick)

    def set_overlay_part(self, part_id: int):
        self.anim_viewer.set_overlay_id(part_id)
        self.anim_viewer.update()


class PartViewerBox(QtWidgets.QGroupBox):
    def __init__(
        self,
        model: anim.model.Model,
        parent: QtWidgets.QWidget,
        anim_id: int,
        clock: utils.clock.Clock,
    ):
        super(PartViewerBox, self).__init__(parent)
        self.model = model
        self.anim_id = anim_id
        self.clock = clock

        self.locale_manager = locale_handler.LocalManager.from_config()
        self.setup_ui()

    def setup_ui(self):
        self.setObjectName("part_viewer_box")
        self._layout = QtWidgets.QGridLayout(self)

        self.part_label = QtWidgets.QLabel(self)
        self.part_label.setObjectName("part_label")
        self.part_label.setText(self.locale_manager.search_key("part"))
        self._layout.addWidget(self.part_label, 0, 0)

        self.part_viewer = anim_viewer.PartViewer(
            self.model,
            [0],
            self.anim_id,
            self.clock,
            self,
            False if self.anim_id == 0 else True,
            True,
        )
        self._layout.addWidget(self.part_viewer, 1, 0)

        self._layout.setColumnStretch(0, 1)
        self._layout.setRowStretch(1, 1)


class AnimViewerPage(QtWidgets.QWidget):
    def __init__(
        self,
        model: anim.model.Model,
        parent: QtWidgets.QWidget,
        anim_id: int,
        update_frame: Callable[..., None],
    ):
        super(AnimViewerPage, self).__init__(parent)
        self.model = model
        self.anim_id = anim_id
        self.update_frame_out = update_frame

        self.locale_manager = locale_handler.LocalManager.from_config()
        self.setup_ui()

    def setup_ui(self):
        self.setObjectName("anim_viewer_page")
        self._layout = QtWidgets.QGridLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        self.anim_viewer_box = AnimViewerBox(
            self.model,
            self,
            self.anim_id,
            self.frame_tick,
        )
        self._layout.addWidget(self.anim_viewer_box, 0, 0)

        self.part_viewer_box = PartViewerBox(
            self.model,
            self,
            self.anim_id,
            self.anim_viewer_box.anim_viewer.clock,
        )
        self._layout.addWidget(self.part_viewer_box, 0, 1)
        total_frames = self.model.get_total_frames()

        interval = total_frames // 30
        if interval == 0:
            interval = 1

        self.frame_slider_group = QtWidgets.QGroupBox(self)
        self.frame_slider_group.setObjectName("frame_slider_group")
        self.frame_slider_layout = QtWidgets.QVBoxLayout(self.frame_slider_group)
        self.frame_slider = utils.label_slider.LabeledSlider(
            0,
            total_frames,
            interval,
            parent=self,
            value_changed_callback=self.update_frame,
        )
        self.frame_slider.setObjectName("frame_slider")
        self.frame_slider.set_value(0)
        self.frame_slider_layout.addWidget(self.frame_slider)
        self._layout.addWidget(self.frame_slider_group, 1, 0, 1, 2)

        self.play_button = QtWidgets.QPushButton(self)
        self.play_button.setObjectName("play_button")
        self.play_svg = utils.asset_loader.AssetLoader.from_config().load_svg(
            "play.svg"
        )
        self.pause_svg = utils.asset_loader.AssetLoader.from_config().load_svg(
            "pause.svg"
        )
        self.play_button.setIcon(self.pause_svg)
        self.play_button.clicked.connect(self.toggle_play)
        self.button_layout = QtWidgets.QHBoxLayout()
        self.button_layout.addWidget(self.play_button)
        self.button_layout.setContentsMargins(0, 0, 0, 0)
        self.button_layout.setSpacing(0)

        self.seek_back_button = QtWidgets.QPushButton(self)
        self.seek_back_button.setObjectName("seek_back_button")
        self.seek_back_svg = utils.asset_loader.AssetLoader.from_config().load_svg(
            "seek_backward.svg"
        )
        self.seek_back_button.setIcon(self.seek_back_svg)
        self.seek_back_button.clicked.connect(self.seek_backwards)
        self.button_layout.addWidget(self.seek_back_button)

        self.seek_forward_button = QtWidgets.QPushButton(self)
        self.seek_forward_button.setObjectName("seek_forward_button")
        self.seek_forward_svg = utils.asset_loader.AssetLoader.from_config().load_svg(
            "seek_forward.svg"
        )
        self.seek_forward_button.setIcon(self.seek_forward_svg)
        self.seek_forward_button.clicked.connect(self.seek_forward)
        self.button_layout.addWidget(self.seek_forward_button)

        self.button_layout.addStretch(1)
        self.current_frame_label = QtWidgets.QLabel(self)
        self.current_frame_label.setObjectName("current_frame_label")
        self.current_frame_label.setText(
            self.locale_manager.search_key("current_frame")
        )
        self.button_layout.addWidget(self.current_frame_label)
        self.current_frame_spinbox = QtWidgets.QSpinBox(self)
        self.current_frame_spinbox.setObjectName("current_frame_spinbox")
        self.current_frame_spinbox.setRange(0, (2**31) - 1)
        self.current_frame_spinbox.setValue(0)
        self.current_frame_spinbox.valueChanged.connect(self.update_frame)
        self.button_layout.addWidget(self.current_frame_spinbox)
        self.button_layout.addStretch(1)

        self.save_frame_button = QtWidgets.QPushButton(self)
        self.save_frame_button.setObjectName("save_frame_button")
        self.save_frame_svg = utils.asset_loader.AssetLoader.from_config().load_svg(
            "dialog_save.svg"
        )
        self.save_frame_button.setIcon(self.save_frame_svg)
        self.save_frame_button.clicked.connect(self.save_frame)
        self.button_layout.addWidget(self.save_frame_button)

        self.frame_slider_layout.addLayout(self.button_layout)
        self.frame_slider_layout.addStretch(1)

        self.model.set_keyframes_sets(self.anim_id)

        self.anim_part_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self.anim_part_splitter.addWidget(self.anim_viewer_box)
        self.anim_part_splitter.addWidget(self.part_viewer_box)
        self._layout.addWidget(self.anim_part_splitter, 0, 0)

        self._layout.setColumnStretch(0, 1)
        self._layout.setRowStretch(0, 1)

    def save_frame(self):
        path = utils.ui_file_dialog.FileDialog(self).select_save_file(
            self.locale_manager.search_key("save_frame"),
            ".",
            filter="PNG (*.png)",
            options=None,
        )
        if path:
            self.anim_viewer_box.anim_viewer.save_frame_to_png(io.path.Path(path))

    def toggle_play(self):
        if self.anim_viewer_box.anim_viewer.clock.is_playing():
            self.anim_viewer_box.anim_viewer.clock.stop()
            self.play_button.setIcon(QtGui.QIcon(self.play_svg))
        else:
            self.anim_viewer_box.anim_viewer.clock.start()
            self.play_button.setIcon(QtGui.QIcon(self.pause_svg))

    def get_frame(self):
        return self.anim_viewer_box.anim_viewer.clock.get_frame()

    def frame_tick(self):
        total_frames = self.model.get_total_frames()
        interval = total_frames // 30
        if interval == 0:
            interval = 1
        self.frame_slider.set_value(self.get_frame())
        self.frame_slider.set_maximum(total_frames)
        self.frame_slider.set_interval(interval)
        try:
            self.current_frame_spinbox.setValue(self.get_frame())
        except OverflowError:
            pass

    def view_parts(self, part_ids: list[int]):
        self.part_viewer_box.part_viewer.part_ids = part_ids
        self.part_viewer_box.part_viewer.update()
        self.anim_viewer_box.set_overlay_part(part_ids[0])

    def seek_backwards(self):
        self.anim_viewer_box.anim_viewer.clock.decrement()
        self.update_frame(self.get_frame())
        self.frame_tick()

    def seek_forward(self):
        self.anim_viewer_box.anim_viewer.clock.increment()
        self.update_frame(self.get_frame())
        self.frame_tick()

    def update_frame(self, frame: int):
        self.update_frame_out(frame)
        self.frame_tick()


class PartLeftPannel(QtWidgets.QWidget):
    def __init__(
        self,
        model: anim.model.Model,
        parent: QtWidgets.QWidget,
        part_id: int,
        on_click: Callable[..., None],
    ):
        super(PartLeftPannel, self).__init__(parent)
        self.model = model
        self.part_id = part_id
        self.part = self.model.get_part(self.part_id)
        self.on_click = on_click
        self.is_highlighted = False

        self.locale_manager = locale_handler.LocalManager.from_config()
        self.setup_ui()

    def setup_ui(self):
        self.setObjectName("part_left_pannel")
        self._layout = QtWidgets.QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        self.wrapper = QtWidgets.QWidget(self)
        self.wrapper.setObjectName("wrapper")
        self.wrapper_layout = QtWidgets.QVBoxLayout(self.wrapper)
        self._layout.addWidget(self.wrapper)

        self.part_id_label = QtWidgets.QLabel(self)
        self.part_id_label.setObjectName("part_id_label")
        self.part_id_label.setText(str(self.part_id))
        self.wrapper_layout.addWidget(self.part_id_label)

        self.part_name_label = QtWidgets.QLabel(self)
        self.part_name_label.setObjectName("part_name_label")
        self.part_name_label.setText(self.part.name)
        self.part_name_label.mouseDoubleClickEvent = self.change_label_to_line_edit
        self.wrapper_layout.addWidget(self.part_name_label)

        self.mousePressEvent = self.view_part

    def change_label_to_line_edit(self, a0: QtGui.QMouseEvent):
        if a0.modifiers() == QtCore.Qt.KeyboardModifier.ShiftModifier:
            return
        self.part_name_line_edit = QtWidgets.QLineEdit(self)
        self.part_name_line_edit.setObjectName("part_name_line_edit")
        self.part_name_line_edit.setText(self.part.name)
        self.part_name_line_edit.editingFinished.connect(self.change_line_edit_to_label)
        self.part_name_line_edit.focusOutEvent = (
            self.change_line_edit_to_label_focus_out
        )
        self.part_name_line_edit.setFocus()
        self.wrapper_layout.addWidget(self.part_name_line_edit)
        self.part_name_label.hide()

    def change_line_edit_to_label(self):
        self.part_name_label.setText(self.part_name_line_edit.text())
        self.part_name_label.show()
        self.part_name_line_edit.hide()
        self.part.name = self.part_name_line_edit.text()

    def change_line_edit_to_label_focus_out(self, a0: QtGui.QFocusEvent):
        self.change_line_edit_to_label()

    def view_part(self, a0: QtGui.QMouseEvent):
        if a0.modifiers() == QtCore.Qt.KeyboardModifier.ShiftModifier:
            self.on_click(self.part_id, False)
        else:
            self.on_click(self.part_id, True)

    def highlight(self):
        self.setStyleSheet("background-color: #2b2b2b;")
        self.part_name_label.setStyleSheet("color: #ffffff;")
        self.part_id_label.setStyleSheet("color: #ffffff;")
        self.is_highlighted = True

    def unhighlight(self):
        self.setStyleSheet("background-color: #1b1b1b;")
        self.part_name_label.setStyleSheet("color: #c5c5c5;")
        self.part_id_label.setStyleSheet("color: #c5c5c5;")
        self.is_highlighted = False


class TimeLine(QtWidgets.QWidget):
    def __init__(
        self,
        model: anim.model.Model,
        parent: QtWidgets.QWidget,
        view_parts: Callable[..., None],
        anim_id: int,
        clock: utils.clock.Clock,
        update_callback: Callable[..., None],
    ):
        super(TimeLine, self).__init__(parent)
        self.model = model
        self.view_parts_out = view_parts
        self.highlighted_parts: list[int] = []
        self.anim_id = anim_id
        self.clock = clock
        self.update_callback = update_callback

        self.locale_manager = locale_handler.LocalManager.from_config()
        self.setup_ui()

    def setup_ui(self):
        self.setObjectName("timeline")

        self._layout = QtWidgets.QGridLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        self.left_pannel_scroll_area = QtWidgets.QScrollArea(self)
        self.left_pannel_scroll_area.setObjectName("left_pannel_scroll_area")
        self.left_pannel_scroll_area.setWidgetResizable(True)
        self.left_pannel_scroll_area.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.left_pannel_scroll_area.setFrameShadow(QtWidgets.QFrame.Shadow.Plain)
        self.left_pannel_scroll_area.setLineWidth(0)
        self.left_pannel_scroll_area.keyPressEvent = self.keyPressEvent

        self.left_pannel_group = QtWidgets.QGroupBox(self.left_pannel_scroll_area)
        self.left_pannel_group.setObjectName("left_pannel_group")
        self.left_pannel_group_layout = QtWidgets.QVBoxLayout(self.left_pannel_group)
        self.left_pannel_group_layout.setContentsMargins(0, 0, 0, 0)
        self.left_pannel_group_layout.setSpacing(0)

        self.left_pannel_scroll_area.setWidget(self.left_pannel_group)
        self._layout.addWidget(self.left_pannel_scroll_area, 1, 0)

        for i, part in enumerate(self.model.mamodel.parts):
            part_widget = PartLeftPannel(self.model, self, part.index, self.view_part)
            self.left_pannel_group_layout.addWidget(part_widget)
            if i != len(self.model.mamodel.parts) - 1:
                separator = QtWidgets.QFrame(self.left_pannel_group)
                separator.setFrameShape(QtWidgets.QFrame.Shape.HLine)
                separator.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
                self.left_pannel_group_layout.addWidget(separator)

        self.time_line_scroll_area = QtWidgets.QScrollArea(self)
        self.time_line_scroll_area.setObjectName("time_line_scroll_area")
        self.time_line_scroll_area.setWidgetResizable(True)
        self.time_line_scroll_area.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.time_line_scroll_area.setFrameShadow(QtWidgets.QFrame.Shadow.Plain)
        self.time_line_scroll_area.setLineWidth(0)
        self.time_line_scroll_area.keyPressEvent = self.keyPressEvent

        self.time_line_group = QtWidgets.QGroupBox(self.time_line_scroll_area)
        self.time_line_group.setObjectName("time_line_group")
        self.time_line_group_layout = QtWidgets.QVBoxLayout(self.time_line_group)
        self.time_line_group_layout.setContentsMargins(0, 0, 0, 0)
        self.time_line_group_layout.setSpacing(0)

        self.time_line_scroll_area.setWidget(self.time_line_group)
        self._layout.addWidget(self.time_line_scroll_area, 1, 1)

        self.left_pannel_time_line_splitter = QtWidgets.QSplitter(self)
        self.left_pannel_time_line_splitter.setOrientation(
            QtCore.Qt.Orientation.Horizontal
        )
        self.left_pannel_time_line_splitter.addWidget(self.left_pannel_scroll_area)
        self.left_pannel_time_line_splitter.addWidget(self.time_line_scroll_area)
        self._layout.addWidget(self.left_pannel_time_line_splitter, 1, 0)

        self.left_pannel_time_line_splitter.setSizes([200, 800])

    def view_part(self, part_id: int, override_highlight: bool = True):
        if part_id < 0:
            return
        if part_id >= len(self.model.mamodel.parts):
            return
        if part_id not in self.highlighted_parts:
            self.highlighted_parts.append(part_id)
        else:
            self.highlighted_parts.remove(part_id)

        if override_highlight:
            self.highlighted_parts = [part_id]

        self.highlight_parts(self.highlighted_parts)
        self.view_parts_out([part_id])
        self.view_keyframes(part_id)
        self.scroll_to_part(part_id)

    def scroll_to_part(self, part_id: int):
        for i in range(self.left_pannel_group_layout.count()):
            item = self.left_pannel_group_layout.itemAt(i)
            if isinstance(item, QtWidgets.QWidgetItem):
                widget = item.widget()
                if isinstance(widget, PartLeftPannel):
                    if widget.part_id == part_id:  # type: ignore
                        self.left_pannel_scroll_area.ensureWidgetVisible(widget)

    def view_keyframes(self, part_id: int):
        # delete items in time line
        main.clear_layout(self.time_line_group_layout)

        part = self.model.get_part(part_id)
        width = self.time_line_group.width() - 40

        for i, keyframes in enumerate(part.keyframes_sets):
            keyframes_widget = keyframe_viewer.PartAnimWidget(
                self.model,
                self,
                part,
                keyframes,
                self.clock,
                width,
                self.update_callback,
            )
            self.time_line_group_layout.addWidget(keyframes_widget)
            if i != len(part.keyframes_sets) - 1:
                separator = QtWidgets.QFrame(self.time_line_group)
                separator.setFrameShape(QtWidgets.QFrame.Shape.HLine)
                separator.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
                self.time_line_group_layout.addWidget(separator)

        self.time_line_group_layout.addStretch(1)

    def set_frame(self, frame: int):
        widgets = self.get_widgets(
            keyframe_viewer.PartAnimWidget, self.time_line_group_layout
        )
        for w in widgets:
            w.set_frame(frame)

    def highlight_parts(self, part_ids: list[int]):
        widgets = self.get_widgets(PartLeftPannel)
        for widget in widgets:
            if widget.part_id in part_ids:
                widget.highlight()
            else:
                widget.unhighlight()

    def keyPressEvent(self, a0: QtGui.QKeyEvent):
        # if focus is on left pannel, scroll to part
        if self.left_pannel_scroll_area.hasFocus():
            shift: bool = a0.modifiers() & QtCore.Qt.KeyboardModifier.ShiftModifier
            if a0.key() == QtCore.Qt.Key.Key_Up:
                self.view_part(
                    self.get_top_highlighted_part() - 1, override_highlight=not shift
                )
            elif a0.key() == QtCore.Qt.Key.Key_Down:
                self.view_part(
                    self.get_bottom_highlighted_part() + 1, override_highlight=not shift
                )
        elif self.time_line_scroll_area.hasFocus():
            widgets = self.get_widgets(
                keyframe_viewer.PartAnimWidget, self.time_line_group_layout
            )
            for widget in widgets:
                widget.move_keyframe(a0)

    def get_top_highlighted_part(self) -> int:
        widgets = self.get_widgets(PartLeftPannel)
        for widget in widgets:
            if widget.is_highlighted:
                return widget.part_id
        return 0

    def get_bottom_highlighted_part(self) -> int:
        widgets = self.get_widgets(PartLeftPannel)
        for widget in reversed(widgets):
            if widget.is_highlighted:
                return widget.part_id
        return 0

    def get_widgets(
        self, _type: Any, layout: Optional[QtWidgets.QLayout] = None
    ) -> list[Any]:
        if layout is None:
            layout = self.left_pannel_group_layout
        widgets: list[Any] = []
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if isinstance(item, QtWidgets.QWidgetItem):
                widget = item.widget()
                if isinstance(widget, _type):
                    widgets.append(widget)
        return widgets


class AnimEditor(QtWidgets.QWidget):
    def __init__(
        self,
        model: anim.model.Model,
        anim_id: int,
    ):
        super(AnimEditor, self).__init__()
        self.model = model
        self.anim_id = anim_id

        self.locale_manager = locale_handler.LocalManager.from_config()
        self.asset_loader = utils.asset_loader.AssetLoader()
        self.setup_ui()

    def setup_ui(self):
        self.resize(900, 700)
        self.setWindowIcon(self.asset_loader.load_icon("icon.png"))
        self.showMaximized()

        self.setWindowTitle(self.locale_manager.search_key("anim_editor_title"))

        self.setObjectName("anim_editor")

        self._layout = QtWidgets.QGridLayout(self)

        self.setup_top_half()
        self.setup_bottom_half()

        self.top_bottom_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        self.top_bottom_splitter.addWidget(self.anim_viewer_page)
        self.top_bottom_splitter.addWidget(self.part_timeline)
        self._layout.addWidget(self.top_bottom_splitter, 0, 0)

        self.top_bottom_splitter.setSizes(
            [int(self.height() * 0.6), int(self.height() * 0.4)]
        )

        self.anim_viewer_page.anim_viewer_box.anim_viewer.start_clock()

    def setup_top_half(self):
        self.anim_viewer_page = AnimViewerPage(
            self.model, self, self.anim_id, self.set_frame
        )
        self._layout.addWidget(self.anim_viewer_page, 0, 0)

    def setup_bottom_half(self):
        self.part_timeline = TimeLine(
            self.model,
            self,
            self.view_parts,
            self.anim_id,
            self.anim_viewer_page.anim_viewer_box.anim_viewer.clock,
            self.update_anim,
        )
        self._layout.addWidget(self.part_timeline, 1, 0)

    def set_frame(self, frame: int):
        self.anim_viewer_page.anim_viewer_box.anim_viewer.set_frame(frame)
        self.anim_viewer_page.anim_viewer_box.update()
        self.anim_viewer_page.part_viewer_box.update()

        self.part_timeline.set_frame(frame)

    def update_anim(self):
        self.anim_viewer_page.anim_viewer_box.update()
        self.anim_viewer_page.part_viewer_box.update()

    def frame_tick(self):
        pass

    def view_parts(self, parts: list[int]):
        self.anim_viewer_page.view_parts(parts)