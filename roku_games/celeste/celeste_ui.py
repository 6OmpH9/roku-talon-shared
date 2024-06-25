from talon import actions

ui_commands = None
ui_keys = None
accent_color = "87ceeb"

def get_commands_and_actions(parrot_config):
    cmds, acts = [], []

    for command, (action, _) in parrot_config.items():
        if action == "":
            continue
        command = command.split(":")[0]
        cmds.append(command)
        acts.append(action)

    return (cmds, acts)

def show_commands(parrot_config, options = {}):
    global ui_commands
    (commands, acts) = get_commands_and_actions(parrot_config)
    (css, div, text, screen) = actions.user.ui_elements(["css", "div", "text", "screen"])
    background_color = options.get("background_color") or "000000"

    screen_css = css(
        id="parrot_commands",
        align_items="flex_end",
        justify_content="flex_start",
    )

    box_css = css(
        margin=16,
        background_color=f"{background_color}66",
        flex_direction="row",
        padding=16,
        gap=16,
    )

    ui_commands = screen(**screen_css)[
        div(**box_css)[
            div(gap=8)[
                text("sound", font_weight="bold"),
                *(text(command) for command in commands),
            ],
            div(gap=8)[
                text("actions", font_weight="bold", color=accent_color),
                *(text(action, color=accent_color) for action in acts)
            ]
        ]
    ]
    ui_commands.show()

def hide_commands():
    global ui_commands
    ui_commands.hide()

key_states = {
    "press": "highlight_briefly",
    "hold": "highlight",
    "release": "unhighlight"
}

def on_key(key, state):
    if ui_keys:
        # this is same as: ui_keys.highlight(key)
        getattr(ui_keys, key_states[state])(key)

def show_keys(options = {}):
    global ui_keys
    (css, div, text, screen) = actions.user.ui_elements(["css", "div", "text", "screen"])

    screen_css = css(
        id="keys",
        justify_content="flex_start",
        align_items="flex_end",
        highlight_color=f"{accent_color}88"
    )

    gamepad_css = css(
        flex_direction="column",
        gap=0,
        margin_top=500,
        margin_right=16
    )

    key_css = css(
        padding=8,
        background_color= "333333dd",
        flex_direction= "row",
        justify_content= "center",
        align_items= "center",
        margin=1,
        width=30,
        height=30
    )

    def key(key_name, text_content, width=30):
        css = {**key_css, 'id': key_name, 'width': width}
        return div(**css)[text(text_content)]

    def blank_key():
        css = {**key_css, "background_color":"33333355" }
        return div(**css)[text(" ")]

    def col():
        return div(flex_direction="column")

    def row():
        return div(flex_direction="row")

    ui_keys = screen(**screen_css)[
        div(**gamepad_css)[
            row()[
                col()[
                    row()[blank_key(), key("up", "↑"), blank_key()],
                    row()[key("left", "←"), key("down", "↓"), key("right", "→")]
                ],
                col()[
                    row()[key("c", "jump"), key("p", "jump 2")],
                    row()[key("x", "dash"), key("t", "demo")]
                ]
            ],
            row()[key("foot_left", "foot1: grab"), key("foot_center", "foot2: move mode")]
        ]
    ]

    ui_keys.show()
    actions.user.game_event_register_on_key(on_key)

def hide_keys():
    actions.user.game_event_unregister_on_key(on_key)
    ui_keys.hide()

def show_ui(parrot_config, options = {}):
    show_commands(parrot_config, options)
    show_keys(options)

def hide_ui():
    hide_commands()
    hide_keys()

def refresh_ui(parrot_config, options = {}):
    hide_commands()
    show_commands(parrot_config, options)

def highlight(key):
    if ui_keys:
        ui_keys.highlight(key)

def unhighlight(key):
    if ui_keys:
        ui_keys.unhighlight(key)

def highlight_briefly(key):
    if ui_keys:
        ui_keys.highlight_briefly(key)