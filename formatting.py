def process_formatted_string(formatted_string: str) -> str:
    # process Minecraft formatting codes §[0-9a-fk-or]
    state = []
    COLORS = list(map(str, range(0, 10))) + ['a', 'b', 'c', 'd', 'e', 'f']

    output = ''
    START_TEMPLATE = '<span class="fmt_{}">'
    END_TEMPLATE = '</span>'


    formatted_string = formatted_string.replace('&', '&amp').replace('>', '&gt').replace('<', '&lt')

    i = 0
    while i < len(formatted_string):
        c = formatted_string[i]
        if c == '§':
            fmt_code = formatted_string[i+1]
            i += 1
            if fmt_code != 'r':
                if len(state) > 0 and state[-1] in COLORS:
                    # pop off, we're overriding it
                    state.pop()
                    output += END_TEMPLATE
                state.append(fmt_code)
                output += START_TEMPLATE.format(fmt_code)
            else:
                for _ in range(len(state)):
                    output += END_TEMPLATE
                state = []
        elif c == '\n':
            output += '<br>'
        else:
            output += c
        i += 1
    for _ in range(len(state)):
        output += END_TEMPLATE

    return output.strip()


if __name__ == '__main__':
    a = '§b>>§6 PLAY KNAFFCRAFT! <3§b <<\n§fSemi-vanilla§b ~§f Survival§b ~§f Economy'
    # a = '                 §aHypixel Network §c[1.8-1.19]\n         §6§lSUMMER §e§lSALE §7§l| §d§lSKYBLOCK 0.14'
    print(process_formatted_string(a))
