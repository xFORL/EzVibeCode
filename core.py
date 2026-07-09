import os
import json

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

try:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config_data = json.load(f)
except Exception as e:
    print(f"Критическая ошибка: не удалось загрузить config.json ({e})")
    config_data = {}

OUTPUT_FILE = config_data.get("OUTPUT_FILE", "all_code_context.txt")
IGNORE_DIRS = set(config_data.get("IGNORE_DIRS", []))
ALLOWED_EXTENSIONS = set(config_data.get("ALLOWED_EXTENSIONS", []))
ALLOWED_FILES = set(config_data.get("ALLOWED_FILES", []))


def is_allowed(filename):
    """Проверяет файл на соответствие спискам разрешенных файлов и расширений."""
    if filename.lower() in ALLOWED_FILES:
        return True
    _, ext = os.path.splitext(filename)
    if ext.lower() in ALLOWED_EXTENSIONS:
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


def generate_tree(dir_path, user_ignores, prefix=""):
    """Рекурсивно строит текстовое дерево структуры проекта."""
    try:
        entries = os.listdir(dir_path)
    except Exception:
        return []

    entries = [e for e in entries if e != OUTPUT_FILE]
    entries.sort(key=lambda x: (not os.path.isdir(os.path.join(dir_path, x)), x.lower()))

    tree_lines = []
    for i, entry in enumerate(entries):
        is_last = (i == len(entries) - 1)
        pointer = "└── " if is_last else "├── "
        next_prefix = prefix + ("    " if is_last else "│   ")

        full_path = os.path.join(dir_path, entry)

        if os.path.isdir(full_path):
            if entry in IGNORE_DIRS or entry in user_ignores:
                f_count = count_files_recursively(full_path)
                tree_lines.append(f"{prefix}{pointer}folder*{entry}* ({f_count} файлов внутри пропущено)")
            else:
                tree_lines.append(f"{prefix}{pointer}{entry}/")
                tree_lines.extend(generate_tree(full_path, user_ignores, next_prefix))
        else:
            if is_allowed(entry) and entry not in user_ignores:
                tree_lines.append(f"{prefix}{pointer}{entry}")
            else:
                tree_lines.append(f"{prefix}{pointer}{entry} (файл пропущен)")

    return tree_lines


def run_aggregation(user_ignores_list, noderevo):
    """Основная функция сборки контекста исходного кода."""
    user_ignores = set(user_ignores_list)
    current_dir = os.getcwd()

    print("Запуск сборки контекста исходного кода...\n")
    if user_ignores:
        print(f"Пользовательские исключения: {', '.join(user_ignores)}\n")

    total_chars = 0
    total_files = 0

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as outfile:
        for root, dirs, files in os.walk(current_dir):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and d not in user_ignores]

            for file in files:
                if file == OUTPUT_FILE or file in user_ignores:
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

            tree_lines = generate_tree(current_dir, user_ignores)
            outfile.write("\n".join(tree_lines))
            total_chars += len(tree_title) + sum(len(line) for line in tree_lines)

    if total_files > 0:
        size_bytes = os.path.getsize(OUTPUT_FILE)
        size_mb = size_bytes / (1024 * 1024)
        approx_tokens = total_chars // 4

        print("\n" + "=" * 50)
        print("СБОР ДАННЫХ УСПЕШНО ЗАВЕРШЕН")
        print(f"Выходной файл:   {OUTPUT_FILE}")
        print(f"Всего файлов:    {total_files}")
        print(f"Размер файла:    {size_mb:.2f} МБ")
        print(f"Объем (токенов): ~{approx_tokens:,}".replace(',', ' '))
        print("=" * 50)
    else:
        print("\nПодходящие файлы для агрегации не обнаружены.")