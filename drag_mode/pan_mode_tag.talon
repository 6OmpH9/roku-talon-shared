mode: user.drag_mode
tag: user.pan_mode
-
<user.drag_mode_target> (to | past) <user.drag_mode_target>:
    user.drag_mode_drag_and_drop(drag_mode_target_1, drag_mode_target_2, 2)

center <user.drag_mode_target>: user.drag_mode_bring_to_center(drag_mode_target, 2)
