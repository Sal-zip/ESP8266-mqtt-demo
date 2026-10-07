# Applicazione di esempio inclusa

Questa pagina descrive il caso d'uso da cui provengono il firmware STM32 e la dashboard della repository. La [guida principale](../README.md) spiega la comunicazione MQTT, la configurazione e l'integrazione in un altro progetto embedded; questo documento serve quando si vuole riprodurre il comportamento specifico degli sketch forniti.

## Provenienza e ruoli

La cartella communication è stata esportata dalla directory comunication del [prototipo Rescue Vest](https://github.com/Sal-zip/Progetto-Neapolis-Innovation-2026/tree/d6e0cdd/Rescue%20Vest%20-%20Prototipo/comunication). Il prototipo invia telemetria e allarmi da un dispositivo indossabile verso una centrale tramite Wi-Fi, broker MQTT e messaggi asincroni.

- **Client STM32:** acquisisce GPS, PPG e MQ2 e riceve eventi gesture. Costruisce i payload JSON e pubblica telemetria, stato e SOS con QoS 1.
- **Server STM32:** sottoscrive i tre topic, accoda i payload e li stampa sulla console ST-LINK.
- **ESP8266 bridge:** uno per ogni STM32, trasporta il flusso TCP del broker via UART.
- **ESP8266 dashboard:** si sottoscrive autonomamente agli stessi topic e ospita la pagina web; non dipende dal server STM32.

La dashboard include etichette e una mappa iniziale del prototipo. È un esempio di frontend: chi usa un altro schema dati può mantenere il bridge e il layer MQTT, ma deve adattare la pagina.

## Connessioni dell'esempio

| Scheda | Segnale | Pin MCU | Periferica |
| --- | --- | --- | --- |
| Client STM32 | ESP8266 TX/RX | PC10/PC11 | USART3, 38400 baud |
| Client STM32 | Console | PA2/PA3 | USART2, 38400 baud |
| Client STM32 | GPS | PA9/PA10 | USART1, 115200 baud |
| Client STM32 | GestureLink | PC1/PC0 | LPUART1 |
| Client STM32 | MAX30102 | PB8/PB9 | I2C1, indirizzo 0x57 |
| Client STM32 | MQ2 analogico | PA1 | ADC1_IN2 |
| Server STM32 | ESP8266 TX/RX | PC4/PC5 | USART1, 38400 baud |
| Server STM32 | Console | PA2/PA3 | USART2, 38400 baud |

I pin sono indicati dal punto di vista della MCU: TX va a RX del modulo e viceversa, con GND comune. Le due STM32 sono schede distinte. Il modulo ESP8266 usa UART0 GPIO1/GPIO3, segnali a 3,3 V; i numeri dei connettori e l'alimentazione dipendono dalla scheda effettiva.

## Dipendenze della build STM32

Il client completo usa package GPS, PPG e MQ2 e il ricevitore GestureLink presenti nel repository sorgente, oltre a ChibiOS 21.11 e alla toolchain ARM. I Makefile esportati conservano i percorsi usati nella build originale, fra cui Sensors, Gesture-Board/Communication, Application e Communication. Poiché questa repository contiene soltanto la sezione communication, occorre integrare i moduli nel progetto ChibiOS o adattare il Makefile e sostituire le sorgenti applicative con quelle del proprio progetto. Gli header app_config.h generati nella [guida principale](../README.md#1-configurare-rete-broker-e-topic) contengono i parametri comuni.

Il bridge può essere usato con entrambe le STM32. La dashboard richiede invece un ESP8266 distinto, con PubSubClient.

## Schema JSON del firmware incluso

Il client genera oggetti con questi campi:

| Campo | Significato |
| --- | --- |
| schemaVersion | Versione dello schema; la dashboard si aspetta 1. |
| type | telemetry, operator_status oppure sos. |
| event | sample, activated, zone_safe, manual_gesture, ppg_emergency o gas_emergency. |
| deviceId | Identità applicativa del dispositivo. |
| eventId | ID dell'evento, formato da deviceId e numero di sequenza. |
| sequence | Contatore dei messaggi dall'avvio. |
| uptimeMs | Tempo dall'avvio della MCU, in millisecondi. |
| gps | Validità, freschezza, coordinate e movimento. |
| ppg | Dati cardiaci e indicatore di emergenza. |
| mq2 | Valore ADC e indicatore di emergenza gas. |

Coordinate latitudeE7 e longitudeE7 sono gradi × 10⁷. SpeedMilliKnots e headingMilliDegrees sono valori scalati × 1000. La dashboard colloca il dispositivo solo quando gps.valid è vero. Mostra un SOS quando type è sos oppure un indicatore di emergenza PPG/MQ2 è vero. I due file in [examples/](../examples/) sono dati fittizi conformi al formato per una prova con mosquitto_pub.

I topic del codice sono configurabili, ma i ruoli restano tre: telemetry, status e sos. Il generatore scrive gli stessi nomi in client, server e dashboard. Per modificare numero dei flussi o forma dei payload occorre modificare la logica applicativa, non soltanto config.json.

## Comportamento delle code

Il client applicativo conserva in RAM fino a otto eventi critici e ritenta un messaggio QoS 1 finché non riceve PUBACK. Dopo un riavvio o un'interruzione di alimentazione prima della conferma, l'evento può andare perso. La telemetria più recente è tenuta separata dagli eventi critici. Il server ha un'inbox statica di otto messaggi; la dashboard conserva gli ultimi venti in RAM e il browser ricostruisce la vista dai messaggi disponibili. QoS 1 può produrre duplicati dopo una riconnessione, perciò un'integrazione che esige unicità deve usare eventId.

La connessione al broker è MQTT/TCP non cifrata. La pagina web è servita direttamente dall'ESP8266 e carica Leaflet e le tessere OpenStreetMap dal browser. 
