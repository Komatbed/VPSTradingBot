import pathlib
import sys

def update_bot_file():
    file_path = pathlib.Path("app/telegram_bot/bot.py")
    if not file_path.exists():
        print(f"File not found: {file_path}")
        return

    content = file_path.read_text(encoding="utf-8")
    lines = content.splitlines()

    new_lines = []
    in_menu_block = False
    skip_lines = False
    
    # New Keyboard Definition
    new_keyboard = [
        '                # USER MENU (Advanced Variant)',
        '                keyboard = {',
        '                    "inline_keyboard": [',
        '                        [',
        '                            {"text": "🔥 Top 3", "callback_data": "cmd:top3"},',
        '                            {"text": "🚀 Sygnały", "callback_data": "cmd:trade"},',
        '                            {"text": "💼 Portfel", "callback_data": "cmd:portfolio"},',
        '                        ],',
        '                        [',
        '                            {"text": "📅 Kalendarz", "callback_data": "cmd:calendar"},',
        '                            {"text": "😱 Fear", "callback_data": "cmd:fear"},',
        '                            {"text": "🗞️ News", "callback_data": "cmd:events"},',
        '                        ],',
        '                        [',
        '                            {"text": "🧮 Calc", "callback_data": "cmd:calc_menu"},',
        '                            {"text": "🔔 Alerty", "callback_data": "cmd:alerts_menu"},',
        '                            {"text": "⚙️ Admin", "callback_data": "cmd:admin"},',
        '                        ],',
        '                        [',
        '                            {"text": "📚 Edukacja", "callback_data": "cmd:learn_menu"},',
        '                            {"text": "👤 Profil", "callback_data": "cmd:profile"},',
        '                        ]',
        '                    ]',
        '                }'
    ]

    for line in lines:
        if 'elif command_type == "menu":' in line:
            new_lines.append(line)
            new_lines.extend(new_keyboard)
            in_menu_block = True
            skip_lines = True
            continue
        
        if in_menu_block and 'url = self._api_url("sendMessage")' in line:
            in_menu_block = False
            skip_lines = False
            new_lines.append(line)
            continue
            
        if skip_lines:
            continue
            
        new_lines.append(line)

    # Now handle the callback part
    # We need to insert the new elifs in _handle_callback
    # Look for 'elif cmd_name == "trade":' and add others after it
    
    final_lines = []
    callback_added = False
    
    for line in new_lines:
        final_lines.append(line)
        if 'elif cmd_name == "trade":' in line and not callback_added:
            final_lines.append('                command = {"type": "trade", "chat_id": chat_id}') # The line we just appended was the condition
            # Wait, the loop appends 'line' which is the condition. The next line in file is the body.
            # I should insert AFTER the body of the matched condition?
            # Or just insert before the final 'else:'?
            pass

    # Actually, simpler approach for callbacks:
    # Find 'elif cmd_name == "admin":' which is near the end of the chain
    # and insert before it.
    
    final_lines_2 = []
    for line in new_lines:
        if 'elif cmd_name == "admin":' in line:
            # Insert new handlers before admin
            final_lines_2.append('            elif cmd_name == "calendar":')
            final_lines_2.append('                command = {"type": "calendar", "chat_id": chat_id}')
            final_lines_2.append('            elif cmd_name == "events":')
            final_lines_2.append('                command = {"type": "events", "chat_id": chat_id}')
            final_lines_2.append('            elif cmd_name == "alerts_menu":')
            final_lines_2.append('                command = {"type": "alerts", "chat_id": chat_id}')
            final_lines_2.append(line) # The admin line
        else:
            final_lines_2.append(line)

    file_path.write_text("\n".join(final_lines_2), encoding="utf-8")
    print("Successfully updated bot.py")

if __name__ == "__main__":
    update_bot_file()
