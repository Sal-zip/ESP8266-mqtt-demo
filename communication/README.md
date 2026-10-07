# Comunicazione

[Client](client/README.md): pubblicazione MQTT di telemetria, stato e allarmi.
[Server](server/README.md): sottoscrizione MQTT e visualizzazione con ESP8266.
Questa cartella è una copia della directory `comunication` del prototipo
Neapolis; il nome qui è normalizzato in `communication`.

I trasporti ESP8266 client/server sono mantenuti separati perché le versioni
fornite differiscono. Il link tra schede gesture e client è nel
[repository sorgente](https://github.com/Sal-zip/Progetto-Neapolis-Innovation-2026/tree/d6e0cdd/Rescue%20Vest%20-%20Prototipo/gesture/link).
Per generare Wi-Fi, broker, topic e identificativi, vedi il [README principale](../README.md#configurazione-unica).

## Pinout e alternate function

| Scheda | Segnale | Pin MCU | Periferica | Alternate function / modalità |
| --- | --- | --- | --- | --- |
| Client | ESP8266 TX / RX | PC10 / PC11 | USART3, 38400 baud | AF7 |
| Client | Console TX / RX | PA2 / PA3 | USART2, 38400 baud | AF7 |
| Client | GestureLink TX / RX | PC1 / PC0 | LPUART1, driver SIO | AF8 |
| Server | ESP8266 TX / RX | PC4 / PC5 | USART1, 38400 baud | AF7 |
| Server | Console TX / RX | PA2 / PA3 | USART2, 38400 baud | AF7 |

I pin sono indicati dal punto di vista della MCU: TX va a RX del dispositivo
collegato e viceversa, con massa comune. Le AF STM32 sono quelle impostate nei
sorgenti. Le schede client, server e gesture sono distinte: i pin ripetuti su
schede diverse non sono condivisi fisicamente. Le tabelle non specificano i
numeri dei connettori, né sostituiscono lo schema di alimentazione dei moduli.
