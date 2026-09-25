# Brus-16

Форк репозитория https://github.com/true-grue/Brus-16

Изменён для работы в составе сайта brus16.ru.

Для сборки эмулятора:
- make.
- C++ compiler.
- SDL3 (Поместить в папку SDL3-3.3.4 или изменить makefile).
- EMCC (https://emscripten.org/docs/getting_started/downloads.html).

`make web`

JS-код в файле brus16_emu.html, для запуска игр используются функции run_from_url и run_from_bytes.

Основной концепт не изменён - запуск по названию игры из файловой системы. В run_from_... актуальный файл игры добавляется как game.bin в FS и эмулятор запускается с аргументом "game.bin".

Файлы brus16.[data, html, js, wasm] заменить в папке static.

