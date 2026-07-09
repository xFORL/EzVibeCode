import argparse
import core

def main():
    parser = argparse.ArgumentParser(description="Агрегатор кода для LLM с выводом дерева проекта")
    parser.add_argument('-t', '--trash', nargs='+', default=[], help="Дополнительный мусор через пробел")
    parser.add_argument('-nd', '--noderevo', action='store_true', help="Отключить генерацию дерева в конце файла")
    args = parser.parse_args()

    core.run_aggregation(args.trash, args.noderevo)

if __name__ == "__main__":
    main()