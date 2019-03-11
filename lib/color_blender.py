def get_range_vals():
    min_lim = None
    max_lim = None

    while min_lim is None:
        try:
            min_lim = float(input('Min value: '))
        except ValueError:
            pass

    while max_lim is None:
        try:
            max_lim = float(input('Max value: '))
        except ValueError:
            pass

    return min_lim, max_lim


def get_rgb():
    while True:
        try:
            h = input('Enter hex: ').lstrip('#')
            if not h or not len(h.lstrip('#')) == 6:
                raise ValueError
            return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
        except ValueError:
            pass


def get_col_count():
    while True:
        try:
            return int(input('How many colours? '))
        except ValueError:
            pass


def rgb_to_hex(color):
    return f"#{''.join(f'{hex(c)[2:].upper():0>2}' for c in color)}"


def main():
    lower, upper = get_range_vals()

    col_count = get_col_count()

    colors = list(zip(*(get_rgb(), get_rgb())))

    output_rgb = list(zip(*
                          [
                              [int(round(c[0] + (i * (c[1] - c[0]) / (col_count - 1)))) for i in range(col_count)]
                              for c in colors
                          ]
                          ))

    output_hex = [rgb_to_hex(c) for c in output_rgb]

    for index, color in enumerate(output_hex):
        value = lower + (index * (abs(lower-upper)) / (col_count - 1))

        print(f"- value: {value}\n  color: '{color.lower()}'")


if __name__ == '__main__':
    main()
