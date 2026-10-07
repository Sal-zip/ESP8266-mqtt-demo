# ESP8266 MQTT demo

Codice di comunicazione del prototipo **Rescue Vest** presentato al Neapolis Summer Campus 2026. Una scheda STM32 pubblica telemetria, stato e SOS tramite MQTT; un ESP8266 le offre un collegamento Wi-Fi/TCP verso Mosquitto. Una seconda STM32 può ricevere i messaggi e un altro ESP8266 può mostrare una dashboard web. La cartella originale `comunication` del [progetto Neapolis](https://github.com/Sal-zip/Progetto-Neapolis-Innovation-2026/tree/d6e0cdd/Rescue%20Vest%20-%20Prototipo/comunication) è qui esportata come [`communication/`](communication/).

Il **broker Mosquitto gira su un computer o server della rete**, non sull'ESP8266. Il bridge non implementa MQTT: trasporta byte TCP fra la STM32 e il broker. La dashboard, invece, è un client MQTT autonomo e ospita la pagina HTTP. La comunicazione attraversa una normale rete Wi-Fi con broker centrale; non crea una rete mesh.

## Indice

- [Architettura e file](#architettura-e-file)
- [Requisiti](#requisiti)
- [Configurazione unica](#configurazione-unica)
- [Avvio rapido: broker e dashboard](#avvio-rapido-broker-e-dashboard)
- [Uso con il firmware STM32](#uso-con-il-firmware-stm32)
- [Integrazione in un altro progetto embedded](#integrazione-in-un-altro-progetto-embedded)
- [Topic e formato dei messaggi](#topic-e-formato-dei-messaggi)
- [Affidabilità e limiti](#affidabilità-e-limiti)
- [Problemi comuni](#problemi-comuni)

## Architettura e file

```text
Sensori / eventi → STM32 client → ESP8266 bridge ─┐
                                                   ├→ broker Mosquitto
Console STM32 ← STM32 server ← ESP8266 bridge ←─────┤
Browser ← HTTP ← ESP8266 dashboard ← MQTT ←────────┘
```

Il server STM32 e la dashboard si sottoscrivono agli stessi tre topic, ma sono indipendenti: per vedere la pagina web non occorre accendere il server STM32. Per la prova rapida si può simulare il client con `mosquitto_pub`.

| Percorso | Funzione |
| --- | --- |
| [`communication/client/`](communication/client/) | Firmware STM32 che acquisisce sensori/eventi, crea JSON e pubblica con QoS 1. |
| [`communication/client/src/`](communication/client/src/) | Trasporto UART↔ESP8266 e pacchetti MQTT 3.1.1. |
| [`communication/client/application/`](communication/client/application/) | Orchestrazione, code in RAM, telemetria e serializzazione JSON. |
| [`communication/server/`](communication/server/) | Firmware STM32 che sottoscrive i topic, accoda i messaggi e li stampa sulla console. |
| [`communication/server/esp8266/neapolis_esp8266_tcp_bridge/`](communication/server/esp8266/neapolis_esp8266_tcp_bridge/) | Sketch da caricare sugli ESP8266 collegati via UART alle STM32; emula i comandi AT usati dal firmware. |
| [`communication/server/esp8266/neapolis_sos_dashboard/`](communication/server/esp8266/neapolis_sos_dashboard/) | Sketch per un ESP8266 **separato**: client MQTT, API HTTP e pagina web. |
| [`tools/configure.py`](tools/configure.py) | Genera tre header di configurazione dallo stesso `config.json` locale. |
| [`examples/`](examples/) | Payload fittizi per una prova senza schede STM32. |

La cartella mantiene i file e la logica del prototipo. L'unica modifica al codice eseguibile è che lo sketch della dashboard legge Wi-Fi, broker e topic da `demo_config.h` generato, anziché dalle vecchie definizioni inline. I due `app_config.h` STM32 sono anch'essi generati; il bridge non contiene credenziali.

## Requisiti

- Per **broker + dashboard**: un ESP8266, Arduino IDE con il [core ESP8266](https://arduino-esp8266.readthedocs.io/en/latest/installing.html), la libreria [PubSubClient](https://github.com/knolleary/pubsubclient), un broker [Eclipse Mosquitto](https://mosquitto.org/download/) raggiungibile via LAN e Python 3 per generare la configurazione. `ESP8266WiFi` ed `ESP8266WebServer` arrivano con il core.
- Per **client/server STM32**: schede e toolchain compatibili con il progetto originale STM32G474RE/ChibiOS 21.11, moduli di sensori e GestureLink del [repository Neapolis](https://github.com/Sal-zip/Progetto-Neapolis-Innovation-2026), più un ESP8266 bridge per ogni STM32. I Makefile esportati sono quelli del progetto originale e dipendono da tale struttura: questa repository **non contiene ChibiOS né i driver dei sensori** e non è da sola un progetto STM32 compilabile.
- Tutti i dispositivi e il broker devono poter comunicare sulla stessa rete IP. Annotare l'IP LAN del computer che ospita Mosquitto; `localhost` o `127.0.0.1` nell'ESP8266 indicano l'ESP stesso.
- Per la mappa della dashboard, il browser deve poter caricare Leaflet e le tessere OpenStreetMap da Internet. La ricezione MQTT e le API locali funzionano anche senza mappa esterna.

## Configurazione unica

1. Clonare questa repository e creare la configurazione locale:

   ```sh
   git clone https://github.com/Sal-zip/ESP8266-mqtt-demo.git
   cd ESP8266-mqtt-demo
   cp config.example.json config.json
   ```

2. In `config.json` sostituire `YOUR_WIFI_SSID`, `YOUR_WIFI_PASSWORD` e `BROKER_LAN_IP_OR_HOSTNAME`. Impostare i tre topic e gli identificativi secondo il progetto. `broker.username` e `broker.password` possono restare vuoti soltanto se il listener Mosquitto consente l'accesso senza autenticazione. I tre MQTT Client ID devono essere diversi fra loro e da quelli degli altri dispositivi.

3. Generare gli header prima di compilare o caricare il firmware:

   ```sh
   python3 tools/configure.py
   ```

   Il comando produce `communication/client/include/app_config.h`, `communication/server/include/app_config.h` e `communication/server/esp8266/neapolis_sos_dashboard/demo_config.h`. `config.json` e gli header generati sono esclusi da Git, così password e indirizzi locali non finiscono nel repository. Dopo ogni cambio di Wi-Fi, broker, topic o ID, rieseguire il comando e ricompilare/caricare le schede interessate.

Il client usa `devices.operator_id` nel JSON; `devices.stm32_client_id` è invece il Client ID della sessione MQTT. Più operatori richiedono `operator_id` e Client ID distinti e una configurazione generata per ciascuna scheda. Per un solo broker, tutti i ruoli devono usare lo stesso host, porta e topic.

## Avvio rapido: broker e dashboard

### 1. Rendere Mosquitto raggiungibile

Installare Mosquitto sul computer della LAN. Dalla versione 2, l'avvio senza listener esplicito accetta normalmente soltanto connessioni locali: l'ESP8266 ha bisogno di un listener raggiungibile in rete ([documentazione Mosquitto](https://mosquitto.org/documentation/migrating-to-2-0/)). Per una prova **su una rete di laboratorio isolata**, un file `mosquitto-demo.conf` può contenere:

```conf
listener 1883 0.0.0.0
allow_anonymous true
```

Avviare `mosquitto -c mosquitto-demo.conf -v` e impostare l'IP LAN del computer in `broker.host`. Non esporre questo listener anonimo a Internet. Se il broker richiede credenziali, configurarle nel broker e in `config.json` secondo la [guida ufficiale Mosquitto](https://www.mosquitto.org/documentation/authentication-methods/). Il codice fornito usa MQTT su TCP **senza TLS**, porta predefinita 1883: il broker deve offrire un listener compatibile.

### 2. Caricare la dashboard

In Arduino IDE, installare `esp8266 by ESP8266 Community` nel Gestore schede e `PubSubClient` nel Gestore librerie. Aprire [`neapolis_sos_dashboard.ino`](communication/server/esp8266/neapolis_sos_dashboard/neapolis_sos_dashboard.ino), selezionare il modello esatto di ESP8266 e la porta seriale, poi caricare. `demo_config.h` deve trovarsi nella stessa cartella dello sketch: è creato dal passo [Configurazione unica](#configurazione-unica). Il monitor seriale a **115200 baud** mostra `Dashboard disponibile su http://<IP_ESP>/` quando il Wi-Fi è connesso. Aprire l'indirizzo da un browser nella stessa rete.

### 3. Inviare un messaggio di prova

Da un terminale con `mosquitto_pub` installato, usare il broker e il topic indicati in `config.json`:

```sh
mosquitto_pub -h <IP_DEL_BROKER> -p 1883 \
  -t 'demo/rescue-vest/telemetry' -q 1 -f examples/telemetry.json
mosquitto_pub -h <IP_DEL_BROKER> -p 1883 \
  -t 'demo/rescue-vest/sos' -q 1 -f examples/sos.json
```

Sostituire `<IP_DEL_BROKER>` e i topic se diversi. Con autenticazione, aggiungere le opzioni client previste dalla propria configurazione Mosquitto. Il browser dovrebbe mostrare `operator-01`, la posizione dimostrativa e l'evento SOS. I JSON sono **dati fittizi**; non provengono dai sensori. Per verificare il broker indipendentemente dalla dashboard: `mosquitto_sub -h <IP_DEL_BROKER> -t 'demo/rescue-vest/#' -v`.

## Uso con il firmware STM32

Lo sketch [`neapolis_esp8266_tcp_bridge.ino`](communication/server/esp8266/neapolis_esp8266_tcp_bridge/neapolis_esp8266_tcp_bridge.ino) va caricato su **ogni ESP8266 usato come bridge**. Non caricare bridge e dashboard sullo stesso modulo. Il bridge riceve SSID, password e host dal firmware STM32 tramite i comandi AT: non serve `demo_config.h` nel suo progetto Arduino. La STM32 esegue MQTT; il bridge gestisce soltanto Wi-Fi e socket TCP trasparente.

| Ruolo STM32 | UART verso bridge ESP8266 | Debug | Baud |
| --- | --- | --- | --- |
| Client | PC10 TX → RX ESP, PC11 RX ← TX ESP (USART3) | USART2 PA2/PA3 | 38400 |
| Server | PC4 TX → RX ESP, PC5 RX ← TX ESP (USART1) | USART2 PA2/PA3 | 38400 |

Unire sempre le masse, usare livelli logici e alimentazione **3,3 V** adeguata per l'ESP8266 e scollegare le linee UART della STM32 durante il caricamento dello sketch se interferiscono con il programmatore. Il bridge usa UART0 ESP8266, GPIO1 TX e GPIO3 RX, a **38400 baud**. La dashboard usa UART0 a **115200 baud** soltanto per il monitor seriale.

Per ricostruire il firmware originale, usare la struttura ChibiOS e i package GPS, PPG, MQ2 e GestureLink del progetto Neapolis; i Makefile inclusi conservano i relativi percorsi originali. Copiare gli header generati nei percorsi `include/` attesi dal build. La configurazione `client` e `server` deve puntare allo **stesso broker** e agli **stessi topic**. Nel progetto originale gli host erano diversi; il generatore elimina questa possibile incongruenza nella copia.

### Che cosa fa il client

1. Inizializza sensori, ricezione gesture, UART e code applicative.
2. Collega il bridge al Wi-Fi e a Mosquitto con i comandi AT implementati dallo sketch.
3. Apre MQTT 3.1.1, compone un JSON `schemaVersion: 1` e pubblica telemetria, stato o SOS con QoS 1.
4. Attende il PUBACK. Se manca, conserva il messaggio in **RAM** e tenta di inviarlo di nuovo dopo la riconnessione. Gli eventi SOS hanno priorità sulla telemetria periodica.

### Che cosa fa il server

Il server STM32 stabilisce una propria sessione MQTT, si sottoscrive ai tre topic con QoS 1 e mette i messaggi in una inbox di dimensione fissa. Un secondo thread li stampa sulla console ST-LINK. La dashboard è un altro subscriber: non riceve dati attraverso il server STM32.

## Integrazione in un altro progetto embedded

Per usare **solo la comunicazione** senza i sensori del prototipo, partire da [`client/src/esp8266_transport.c`](communication/client/src/esp8266_transport.c), [`client/src/mqtt_client.c`](communication/client/src/mqtt_client.c) e dai rispettivi header. Il trasporto richiede `SerialDriver` e primitive temporali ChibiOS; su un'altra MCU/RTOS occorre adattare le funzioni dichiarate in `esp8266_transport.h`, mantenendo il flusso di byte MQTT invariato. Per ricevere, usare analogamente `server/src/` e la callback di `server/main.c` come esempio.

Nel proprio codice applicativo:

1. Inizializzare la UART del bridge a 38400 baud e una console separata per i log. Inizializzare `esp8266_transport_t` e `mqtt_client_t` come negli entry point forniti.
2. Chiamare `esp8266_transport_connect()`, poi `mqtt_client_open()`. Entrambe devono riuscire prima di pubblicare o sottoscrivere.
3. Creare un topic e un payload di lunghezza esplicita. Il publisher STM32 usa `mqtt_client_publish_qos1(...)`; in assenza di messaggi, chiamare `mqtt_client_yield(...)` per elaborare il keep-alive. Dopo un errore, ricostruire la connessione e ritentare **lo stesso payload** finché arriva PUBACK.
4. Se si usa la dashboard fornita, rispettare lo [schema JSON](#topic-e-formato-dei-messaggi) e gli stessi tre topic. La pagina scarta i payload che non sono JSON validi o che non contengono `schemaVersion: 1` e un `deviceId` non vuoto.

Gli header `include/` sono l'interfaccia per l'integrazione. Per altri pin, driver seriali, schede o librerie Wi-Fi serve adattare il livello hardware: la configurazione JSON rende immediati host/topic/ID, ma non sostituisce il porting dell'HAL.

## Topic e formato dei messaggi

I nomi sono modificabili in `config.json`; questi sono quelli di esempio:

| Topic | Publisher | Subscriber | Contenuto |
| --- | --- | --- | --- |
| `demo/rescue-vest/telemetry` | Client STM32 | Server STM32, dashboard | Campione periodico GPS/PPG/MQ2. |
| `demo/rescue-vest/status` | Client STM32 | Server STM32, dashboard | Attivazione operatore, zona sicura. |
| `demo/rescue-vest/sos` | Client STM32 | Server STM32, dashboard | SOS manuale, PPG o gas. |

I payload JSON usano `schemaVersion: 1`, `type`, `event`, `deviceId`, `eventId`, `sequence`, `uptimeMs` e gli oggetti `gps`, `ppg`, `mq2`. `event` può essere `sample`, `activated`, `zone_safe`, `manual_gesture`, `ppg_emergency` o `gas_emergency`. Coordinate `latitudeE7`/`longitudeE7` sono interi in gradi × 10⁷; `speedMilliKnots` e `headingMilliDegrees` sono valori scalati × 1000. La dashboard usa `gps.valid` per collocare l'operatore sulla mappa, visualizza BPM e ADC grezzo e considera SOS i messaggi `type: "sos"` o quelli con `ppg.emergency`/`mq2.emergency` veri. Vedi i [due payload completi](examples/) per un esempio riproducibile.

## Affidabilità e limiti

- Il client STM32 pubblica con **QoS 1** e attende PUBACK; la consegna è *almeno una volta*, quindi in caso di ritrasmissione un subscriber può vedere duplicati. `eventId` e `sequence` aiutano il progetto integratore a deduplicare.
- La sessione del server STM32 è persistente nel protocollo MQTT. Il suo Client ID deve restare stabile e il broker deve conservare lo stato previsto; le code applicative del client e del server restano **solo in RAM**. Un'interruzione di alimentazione può perdere eventi ancora non confermati. La dashboard mantiene in RAM gli ultimi **20 messaggi** e la pagina ricostruisce la vista leggendo questi eventi.
- La dashboard usa Leaflet da CDN e tessere OpenStreetMap. La mappa iniziale è centrata su Napoli, come nel prototipo; si ricentra quando arrivano coordinate valide.
- Le connessioni MQTT/TCP e HTTP sono **non cifrate**. Per un impiego fuori da una LAN controllata servono autenticazione, TLS e ulteriori controlli di accesso.
- La versione qui esportata non contiene il successivo backend web sviluppato per la fiera. La pagina è ospitata direttamente dallo sketch ESP8266 del prototipo.

## Problemi comuni

| Sintomo | Controllo |
| --- | --- |
| `tools/configure.py` rifiuta la configurazione | Sostituire i placeholder e controllare che i tre Client ID e i tre topic siano distinti. |
| ESP connesso al Wi-Fi ma MQTT disconnesso | Usare l'IP **LAN del broker**, verificare listener sulla porta 1883, firewall e credenziali. Mosquitto avviato senza listener può accettare solo `localhost`. |
| Il broker riceve messaggi ma la dashboard è vuota | Confrontare i topic; controllare `schemaVersion`, `deviceId` e che il JSON sia valido. Guardare `/api/status` e `/api/messages` dall'IP della dashboard. |
| Dashboard visibile senza mappa | Il browser deve poter caricare Leaflet e OpenStreetMap; verificare la connessione Internet del browser. |
| STM32 non comunica col bridge | Controllare UART a 38400, TX↔RX incrociati, massa comune, alimentazione 3,3 V e firmware bridge caricato. Leggere la console di debug STM32, non la UART MQTT binaria. |
| Ricezione intermittente o duplicati | QoS 1 può ritrasmettere; usare `eventId` per deduplicare e verificare stabilità di Wi-Fi/broker. |

## Provenienza

Codice esportato dal [prototipo Rescue Vest, commit `d6e0cdd`](https://github.com/Sal-zip/Progetto-Neapolis-Innovation-2026/tree/d6e0cdd/Rescue%20Vest%20-%20Prototipo/comunication). Nella copia sono state generalizzate solo le impostazioni Wi-Fi, broker e topic, preservando la logica del prototipo testato. Le dipendenze ChibiOS, core Arduino ESP8266, PubSubClient, Mosquitto, Leaflet e OpenStreetMap appartengono ai rispettivi progetti.
