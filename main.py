import argparse
import core

def main():
    parser = argparse.ArgumentParser(description="Агрегатор кода для LLM с выводом дерева проекта")
    parser.add_argument('-t', '--trash', nargs='+', default=[], help="Дополнительный мусор через пробел")
    parser.add_argument('-nd', '--noderevo', action='store_true', help="Отключить генерацию дерева в конце файла")
    parser.add_argument('-fn', '--filename', type=str, default=None, help="Переопределить имя выходного файла")
    parser.add_argument('-cf', '--copyfile', action='store_true', help="Скопировать физический файл в буфер обмена")
    parser.add_argument('-ct', '--copytext', action='store_true', help="Скопировать весь текст в буфер обмена")
    args = parser.parse_args()

    core.run_aggregation(
        user_ignores_list=args.trash,
        noderevo=args.noderevo,
        custom_filename=args.filename,
        copy_file=args.copyfile,
        copy_text=args.copytext
    )

if __name__ == "__main__":
    main()