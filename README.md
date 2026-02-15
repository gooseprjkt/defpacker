# DefPacker

DefPacker - упаковщик архивов, надежно защищающий файлы

## Фишки

- **Глубокая обфускация**: Защита различными путающими названиями
- **Фейковые файлы**: Генерация файлов с похожим размеров
- **Шифрование**: AES-256 защита
- **Странный манифест**: Простой, но странный на вид энкодинг
- **Форматы**: Поддержка ZIP, TAR.GZ, TAR.BZ2, TAR.XZ, 7Z
- **Энкодер**: Встроенный энкодер с мусором

## Установка зависимостей

```bash
pip install -r requirements.txt
```

## Использование

### Командная строка

```bash
# Упаковка
python -m defpacker pack input_dir/ output.zip

# Упаковка на ваш вкус
python -m defpacker pack input_dir/ output.7z --levels 5 --types short longer w_like --encrypt --format 7z

# Распаковка
python -m defpacker unpack protected.zip output_dir/
```

### Programmatic Usage

```python
from defpacker.core import DefPacker

packer = DefPacker()
packer.pack(
    input_path="input_dir/",
    output_path="output.zip",
    obfuscation_levels=3,
    obfuscation_types=['short', 'longer', 'w_like'],
    encryption_password="secure_password"
)

packer.unpack(
    archive_path="output.zip",
    output_dir="restored/",
    decryption_password="secure_password"
)
```

## Архитектура

- `core/`: Главная логика
- `encoder/`: Энкодер
- `cli/`: Командный интерфейс
