import os
import mel_parser


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
    string inputStr(string str){
        int a = 5;
        int b;
        b = a;
    }
    '''
    prog = mel_parser.parse(prog)
    print(*prog.tree, sep=os.linesep)


if __name__ == "__main__":
    main()
