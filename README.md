# phy62xx_patch
Mod tool for Bluetooth Toys with Phy62xx / ST17H66B2

## Connection
Either using usb or uart-to-usb converter (solder cables to TX + RX testpoints on pcb). In order to dump, shortly connect TM testpad with VCC and release immediately to enter test mode for dumping/flashing.

## Documentation
[PHY6222/6252 SDK 3.11](https://github.com/zxf1023818103/release_bbb_sdk-PHY62XX_SDK_3.1.1)
[TH04 Teardown](https://github.com/Asgeirs-com/Tuya-TH04-PHY6252-1.5-teardown)
[PHY6222 Datasheet](https://github.com/SoCXin/PHY6222/blob/master/docs/PHY6222_BLE_SoC_Datasheet_v1.3_20211222.pdf)
[ST17H66B2 Datasheet](https://www.lenzetech.com/public/store/pdf/jsggs/ST17H66B2_BLE_SoC_Datasheet_v1.1.2.pdf)

## Dumping flash

- 0x11000000 is the flash addr
- 0x4000 is the flash size (256K), use 0x8000 for 512K flash
- You may need to also set the specific uart baudrate (1000000 is common) using -b option
- You can get the rdwr_phy62x2 flashtool [here](https://github.com/pvvx/PHY62x2)

```
python rdwr_phy62x2.py -p /dev/ttyUSB0 -b 1000000 -r rc 0x11000000 0x40000 flash.bin
```

## Fixing flash checksums

```bash
python parse_flash.py flash.bin
```

## Writing flash

```bash
python rdwr_phy62x2.py -p /dev/ttyUSB0 -b 1000000 we 0 flash.bin.patched
```

## Device list/testpoints
[here] (https://github.com/MakersFunDuck/humidity-temperature-sensor-TH05F)
