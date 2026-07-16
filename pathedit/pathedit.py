import os
import sys
import winreg
import ctypes

def is_admin():
    """Проверяет, запущен ли скрипт с правами Администратора."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False

def run_as_admin(target_dir):
    """Перезапускает текущий скрипт/exe с правами Администратора,
    передавая выбранный путь в параметрах, чтобы не спрашивать пользователя дважды.
    """
    if getattr(sys, 'frozen', False):
        executable = sys.executable
        arguments = f'--system --path "{target_dir}"'
    else:
        executable = sys.executable
        script_path = os.path.abspath(sys.argv[0])
        arguments = f'"{script_path}" --system --path "{target_dir}"'

    print("\n[Запрос прав] Для системной установки требуются права Администратора...")
    print("Пожалуйста, подтвердите запрос в появившемся окне Windows UAC.")

    try:
        result = ctypes.windll.shell32.ShellExecuteW(
            None, 
            "runas", 
            executable, 
            arguments, 
            None, 
            1
        )
        return result > 32
    except OSError as e:
        if getattr(e, 'winerror', 0) == 1223:
            print("\n[Отмена] Вы отклонили запрос прав Администратора.")
        else:
            print(f"\n[Ошибка] Не удалось запросить права: {e}")
        return False

def broadcast_settings_change():
    """Сообщает Windows об обновлении переменных окружения,
    чтобы новые консоли сразу увидели изменения без перезагрузки ПК.
    """
    try:
        HWND_BROADCAST = 0xFFFF
        WM_SETTINGCHANGE = 0x001A
        SMTO_ABORTIFHUNG = 0x0002
        
        ctypes.windll.user32.SendMessageTimeoutW(
            HWND_BROADCAST, 
            WM_SETTINGCHANGE, 
            0, 
            "Environment", 
            SMTO_ABORTIFHUNG, 
            5000, 
            ctypes.byref(ctypes.c_long())
        )
    except Exception:
        pass

def add_to_path(folder_path, system_wide=False):
    """Записывает переданный путь в PATH (пользовательский или системный)."""
    folder_path = os.path.abspath(folder_path)
    if not os.path.isdir(folder_path):
        print(f"Ошибка: Путь '{folder_path}' не существует.")
        return False

    evc_exe_path = os.path.join(folder_path, "EVC.exe")
    if not os.path.exists(evc_exe_path):
        print(f"\n[Внимание] В папке '{folder_path}' не найден файл EVC.exe!")
        print("Убедитесь, что вы распаковали ВЕСЬ архив в эту папку перед настройкой.")
        confirm = input("Вы всё равно хотите продолжить? (y/n): ").strip().lower()
        if confirm not in ['y', 'yes', 'д', 'да']:
            return False

    try:
        if system_wide:
            root_key = winreg.HKEY_LOCAL_MACHINE
            subkey = r"System\CurrentControlSet\Control\Session Manager\Environment"
            mode_name = "СИСТЕМНЫЙ PATH (для всех пользователей)"
        else:
            root_key = winreg.HKEY_CURRENT_USER
            subkey = "Environment"
            mode_name = "ПОЛЬЗОВАТЕЛЬСКИЙ PATH (только для вас)"

        key = winreg.OpenKey(root_key, subkey, 0, winreg.KEY_ALL_ACCESS)
        try:
            current_path, data_type = winreg.QueryValueEx(key, "Path")
        except FileNotFoundError:
            current_path = ""
            data_type = winreg.REG_EXPAND_SZ

        paths = [p.strip() for p in current_path.split(";") if p.strip()]
        if folder_path in paths:
            print(f"\n[Инфо] Этот путь уже есть в {mode_name}:")
            print(f"-> {folder_path}")
            winreg.CloseKey(key)
            return True

        paths.append(folder_path)
        new_path = ";".join(paths)
        winreg.SetValueEx(key, "Path", 0, data_type, new_path)
        winreg.CloseKey(key)

        print(f"\n[УСПЕШНО] Путь успешно добавлен в {mode_name}!")
        print(f"Добавлен путь: {folder_path}")
        
        broadcast_settings_change()
        return True

    except PermissionError:
        print(f"\n[Ошибка] Отказано в доступе к {mode_name}!")
        print("Запустите утилиту от имени Администратора для записи в системный реестр.")
        return False
    except Exception as e:
        print(f"\nПроизошла непредвиденная ошибка при записи реестра: {e}")
        return False

def main():
    system_flag = "--system" in sys.argv
    path_arg = None
    if "--path" in sys.argv:
        try:
            idx = sys.argv.index("--path")
            path_arg = sys.argv[idx + 1]
        except (ValueError, IndexError):
            pass

    if system_flag and path_arg:
        print("=== EzVibeCode Path Editor (Режим Администратора) ===")
        print(f"Выполняется автоматическая запись системного пути...\n")
        if add_to_path(path_arg, system_wide=True):
            print("\n" + "=" * 60)
            print("Готово! Системный путь успешно обновлен.")
            print("Перезапустите открытые терминалы, чтобы начать пользоваться EVC.")
            print("=" * 60)
        input("\nНажмите Enter для выхода...")
        return

    print("=== EzVibeCode Path Editor ===")
    print("Этот инструмент сделает EVC доступным из любого терминала.\n")

    if getattr(sys, 'frozen', False):
        current_dir = os.path.dirname(os.path.abspath(sys.executable))
    else:
        current_dir = os.path.dirname(os.path.abspath(__file__))

    print(f"Рекомендуемый путь (папка запуска): {current_dir}")
    user_input = input("Введите путь вручную или нажмите Enter, чтобы использовать рекомендуемый: ").strip()
    target_dir = user_input if user_input else current_dir

    print("\nВыберите тип установки PATH:")
    print(" [1] Только для текущего пользователя (Рекомендуется, не требует прав админа)")
    print(" [2] Для всей системы (Для всех пользователей и служб, требует права админа)")
    
    choice = input("\nВведите номер варианта (1 или 2): ").strip()

    if choice == "2":
        if not is_admin():
            run_as_admin(target_dir)
        else:
            add_to_path(target_dir, system_wide=True)
            input("\nНажмите Enter для выхода...")
    else:
        if add_to_path(target_dir, system_wide=False):
            print("\n" + "=" * 60)
            print("Готово! Изменения применились.")
            print("Перезапустите открытые терминалы или VS Code, чтобы начать пользоваться EVC.")
            print("=" * 60)
        input("\nНажмите Enter для выхода...")

if __name__ == "__main__":
    main()