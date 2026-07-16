import os
import json
import sys
import platform

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

try:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config_data = json.load(f)
except Exception as e:
    print(f"Критическая ошибка: не удалось загрузить config.json ({e})")
    print(f"Путь поиска конфига: {CONFIG_PATH}")
    config_data = {}

DEFAULT_FILENAME = config_data.get("FILENAME", "all_code_context.txt")

# Белый список
ALLOWED_DIRS = {d.lower() for d in config_data.get("ALLOWED_DIRS", [])}
ALLOWED_FILES = {f.lower() for f in config_data.get("ALLOWED_FILES", [])}
ALLOWED_EXTENSIONS = {e.lower() for e in config_data.get("ALLOWED_EXTENSIONS", [])}

# Черный список
IGNORE_DIRS = {d.lower() for d in config_data.get("IGNORE_DIRS", [])}
IGNORE_FILES = {f.lower() for f in config_data.get("IGNORE_FILES", [])}
IGNORE_EXTENSIONS = {e.lower() for e in config_data.get("IGNORE_EXTENSIONS", [])}


def is_dir_allowed(dirname, user_ignores):
    """Проверяет, разрешено ли заходить в директорию."""
    dir_lower = dirname.lower()
    
    # Строгий запрет (user_ignores уже приведен к нижнему регистру в run_aggregation)
    if dir_lower in IGNORE_DIRS or dir_lower in user_ignores:
        return False
    if ALLOWED_DIRS and dir_lower not in ALLOWED_DIRS:
        return False
    return True


def is_allowed(filename):
    """Проверяет файл по черным и белым спискам."""
    name_lower = filename.lower()
    
    # 1. ЧЕРНЫЕ СПИСКИ
    if name_lower in IGNORE_FILES:
        return False
        
    for ext in IGNORE_EXTENSIONS:
        if name_lower.endswith(ext):
            return False
            
    # 2. БЕЛЫЕ СПИСКИ
    if name_lower in ALLOWED_FILES:
        return True
        
    for ext in ALLOWED_EXTENSIONS:
        if name_lower.endswith(ext):
            return True
            
    return False

def generate_header(filepath, root_dir):
    """Генерирует информационный заголовок-разделитель для файла."""
    rel_path = os.path.relpath(filepath, root_dir)
    border = "|" + "-" * 70 + "|"
    title = f"| {rel_path.center(68)} |"
    return f"\n\n{border}\n{title}\n{border}\n\n"


def count_files_recursively(dir_path):
    """Рекурсивно подсчитывает общее количество файлов внутри директории."""
    count = 0
    for _, _, files in os.walk(dir_path):
        count += len(files)
    return count


def generate_tree(dir_path, user_ignores, output_file, prefix=""):
    """Рекурсивно строит текстовое дерево структуры проекта."""
    try:
        entries = os.listdir(dir_path)
    except Exception:
        return []

    # Регистронезависимое исключение выходного файла из структуры дерева
    entries = [e for e in entries if e.lower() != output_file.lower()]
    entries.sort(key=lambda x: (not os.path.isdir(os.path.join(dir_path, x)), x.lower()))

    tree_lines = []
    for i, entry in enumerate(entries):
        is_last = (i == len(entries) - 1)
        pointer = "└── " if is_last else "├── "
        next_prefix = prefix + ("    " if is_last else "│   ")

        full_path = os.path.join(dir_path, entry)

        if os.path.isdir(full_path):
            if not is_dir_allowed(entry, user_ignores):
                f_count = count_files_recursively(full_path)
                tree_lines.append(f"{prefix}{pointer}folder*{entry}* ({f_count} файлов внутри пропущено)")
            else:
                tree_lines.append(f"{prefix}{pointer}{entry}/")
                tree_lines.extend(generate_tree(full_path, user_ignores, output_file, next_prefix))
        else:
            # Приводим к нижнему регистру для сверки с пользовательскими исключениями
            if is_allowed(entry) and entry.lower() not in user_ignores:
                tree_lines.append(f"{prefix}{pointer}{entry}")
            else:
                tree_lines.append(f"{prefix}{pointer}{entry} (файл пропущен)")

    return tree_lines


def copy_text_to_clipboard(text):
    """Копирует сырой текст в буфер обмена (CF_UNICODETEXT) на Windows."""
    if platform.system() != "Windows":
        print("[Инфо] Копирование текста в буфер поддерживается только на ОС Windows.")
        return False
    try:
        import ctypes
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        if not user32.OpenClipboard(None):
            return False
        user32.EmptyClipboard()

        data = text.encode('utf-16le') + b'\x00\x00'
        GMEM_MOVEABLE = 0x0002
        h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
        lp_mem = kernel32.GlobalLock(h_mem)
        ctypes.memmove(lp_mem, data, len(data))
        kernel32.GlobalUnlock(h_mem)

        user32.SetClipboardData(13, h_mem)
        user32.CloseClipboard()
        return True
    except Exception as e:
        print(f"Ошибка копирования текста: {e}")
        return False


def copy_file_to_clipboard(filepath):
    """Копирует сам физический файл в буфер обмена (CF_HDROP),
    позволяя вставить его как файл (например, в Проводник или чаты).
    """
    if platform.system() != "Windows":
        print("[Инфо] Копирование файлов в буфер поддерживается только на ОС Windows.")
        return False
    try:
        import ctypes
        abs_path = os.path.abspath(filepath)
        if not os.path.exists(abs_path):
            print(f"Ошибка: Файл '{abs_path}' не найден для копирования.")
            return False

        struct_size = 20
        path_bytes = abs_path.encode('utf-16le') + b'\x00\x00\x00\x00'
        total_size = struct_size + len(path_bytes)

        GMEM_MOVEABLE = 0x0002
        h_mem = ctypes.windll.kernel32.GlobalAlloc(GMEM_MOVEABLE, total_size)
        lp_mem = ctypes.windll.kernel32.GlobalLock(h_mem)

        struct_bytes = (
            struct_size.to_bytes(4, 'little') + 
            b'\x00' * 8 + 
            b'\x00' * 4 + 
            b'\x01\x00\x00\x00'
        )

        ctypes.memmove(lp_mem, struct_bytes, struct_size)
        ctypes.memmove(lp_mem + struct_size, path_bytes, len(path_bytes))
        ctypes.windll.kernel32.GlobalUnlock(h_mem)

        user32 = ctypes.windll.user32
        if not user32.OpenClipboard(None):
            return False
        user32.EmptyClipboard()
        user32.SetClipboardData(15, h_mem)
        user32.CloseClipboard()
        return True
    except Exception as e:
        print(f"Ошибка копирования файла: {e}")
        return False


def run_aggregation(user_ignores_list, noderevo, custom_filename=None, copy_file=False, copy_text=False):
    """Основная функция сборки контекста исходного кода."""
    # Приводим пользовательские исключения к нижнему регистру для регистронезависимости
    user_ignores = {x.lower() for x in user_ignores_list}
    current_dir = os.getcwd()
    
    output_file = custom_filename if custom_filename else DEFAULT_FILENAME

    print("Запуск сборки контекста исходного кода...\n")
    if user_ignores:
        print(f"Пользовательские исключения: {', '.join(user_ignores)}\n")

    total_chars = 0
    total_files = 0

    with open(output_file, 'w', encoding='utf-8') as outfile:
        for root, dirs, files in os.walk(current_dir):
            dirs[:] = [d for d in dirs if is_dir_allowed(d, user_ignores)]

            for file in files:
                # Регистронезависимая проверка имени файла для предотвращения бесконечной рекурсии
                if file.lower() == output_file.lower() or file.lower() in user_ignores:
                    continue

                if is_allowed(file):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as infile:
                            content = infile.read()
                        if not content.strip():
                            continue

                        header = generate_header(filepath, current_dir)
                        outfile.write(header)
                        outfile.write(content)

                        total_chars += len(header) + len(content)
                        total_files += 1
                        print(f"Обработан файл: {file}")
                    except UnicodeDecodeError:
                        print(f"Пропуск {file} (ошибка кодировки)")
                    except Exception as e:
                        print(f"Пропуск {file} (ошибка чтения: {e})")

        if not noderevo:
            print("\nГенерация структуры проекта...")
            border = "=" * 70
            tree_title = f"\n\n{border}\n| {'СТРУКТУРА ПРОЕКТА / ДЕРЕВО'.center(66)} |\n{border}\n\n"
            outfile.write(tree_title)

            root_name = os.path.basename(current_dir) or current_dir
            outfile.write(f"{root_name}/\n")

            tree_lines = generate_tree(current_dir, user_ignores, output_file)
            outfile.write("\n".join(tree_lines))
            total_chars += len(tree_title) + sum(len(line) for line in tree_lines)

    if total_files > 0:
        size_bytes = os.path.getsize(output_file)
        size_mb = size_bytes / (1024 * 1024)
        approx_tokens = total_chars // 4

        print("\n" + "=" * 50)
        print("СБОР ДАННЫХ УСПЕШНО ЗАВЕРШЕН")
        print(f"Выходной файл:   {output_file}")
        print(f"Всего файлов:    {total_files}")
        print(f"Размер файла:    {size_mb:.2f} МБ")
        print(f"Объем (токенов): ~{approx_tokens:,}".replace(',', ' '))
        print("=" * 50)

        if copy_text:
            try:
                with open(output_file, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                if copy_text_to_clipboard(file_content):
                    print("\n[Буфер] Текст файла успешно скопирован в буфер обмена (Ctrl+V в чат)!")
            except Exception as e:
                print(f"\n[Ошибка] Не удалось скопировать текст в буфер: {e}")

        elif copy_file:
            if copy_file_to_clipboard(output_file):
                print("\n[Буфер] Сам файл успешно скопирован в буфер обмена (можно вставить файл в мессенджер)!")

    else:
        print("\nПодходящие файлы для агрегации не обнаружены.")