import os
import sys
import traceback

import mel_parser
import msil
import semantic_base
import semantic_checker


def main():
    prog = '''
    int main(int a) {
        int g, g2 = g, g = 90;
        i++;
        --i;
        bool op1 = true;
        bool a = !op1;
        if (!op1){
            a = 1;
        }
        int c = g > a ? 3 : 4;
        a = input(); b = input();  /* comment 1
        c = input();
        */
        do {
            a = b + 1;
        } while(a < b);
        while(a < b) {
            a = c + b;
        }
        for (int i = 0, j = 8; ((i <= 5)) && g; i++, print(5))
            for(; a < b;)
                if (a > 7 + b) {
                    c = a + b * (2 - 1) + 0;  // comment 2
                    b = "98\tура";
                }
                else if (f)
                    output(--c + 1, 89.89);
        for(;;);
    }
    
    string inputStr(string str){
        int a = 5;
        int b;
        b = a;
    }
    '''
    prog2 = '''
    int main2(int a){
        int b = 2;
        b += a;
        print(b);
        return b;  
    }
    
    void main() {
      int f = main2(5);
    }
    '''
    #prog = mel_parser.parse(prog2)
    #print(*prog.tree, sep=os.linesep)
    #program.execute(prog2)

    msil_only = True

    if not msil_only:
        print('ast:')
    try:
        prog = mel_parser.parse(prog2)
    except Exception as e:
        print('Ошибка: {}'.format(e.__str__()), file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        exit(1)

    if not msil_only:
        print(*prog.tree, sep=os.linesep)
        print()
        print('semantic-check:')
    try:
        checker = semantic_checker.SemanticChecker()
        scope = semantic_checker.prepare_global_scope()
        checker.semantic_check(prog, scope)
        if not msil_only:
            print(*prog.tree, sep=os.linesep)
            print()
    except semantic_base.SemanticException as e:
        print('Ошибка: {}'.format(e.message), file=sys.stderr)
        exit(2)

    if not msil_only:
        print('msil:')
    try:
        gen = msil.MsilCodeGenerator()
        gen.gen_program(prog)
        print(*gen.code, sep=os.linesep)
    except msil.MsilException or Exception as e:
        print('Ошибка: {}'.format(e.message), file=sys.stderr)
        exit(3)


if __name__ == "__main__":
    main()
