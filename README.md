# ESP8266 MQTT communication demo

Demo riutilizzabile per collegare un firmware embedded a un broker MQTT tramite ESP8266 e per visualizzare messaggi in una pagina web ospitata da un secondo ESP8266. I parametri di rete e i topic si impostano in un solo file locale, senza modificare il codice sorgente.

La repository contiene due percorsi indipendenti:
- **Bridge UART → Wi-Fi/TCP:** La scheda principale compone e interpreta i pacchetti MQTT; lo sketch ESP8266 trasporta byte tra UART e broker. Il firmware fornito per la scheda principale usa STM32G474RE e ChibiOS.
- **Dashboard MQTT → HTTP:** Un altro ESP8266 si connette direttamente al broker, riceve i messaggi e serve una pagina web. Può funzionare anche senza le schede STM32.

Il broker Mosquitto gira su un computer o server raggiungibile nella rete, non sull'ESP8266.

## Contenuto

| Percorso | Scopo |
| --- | --- |
| [communication/client/](communication/client/) | Publisher MQTT per STM32, trasporto ESP8266 e applicazione di esempio. |
| [communication/server/](communication/server/) | Subscriber MQTT per STM32 con coda di messaggi e console di debug. |
| [communication/server/esp8266/neapolis_esp8266_tcp_bridge/](communication/server/esp8266/neapolis_esp8266_tcp_bridge/) | Sketch bridge da caricare sugli ESP8266 collegati via UART a una STM32. |
| [communication/server/esp8266/neapolis_sos_dashboard/](communication/server/esp8266/neapolis_sos_dashboard/) | Sketch dashboard: MQTT, API HTTP e pagina web sullo stesso ESP8266. |
| [tools/configure.py](tools/configure.py) | Generazione degli header dai parametri locali. |
| [examples/](examples/) | Due payload dimostrativi per verificare broker e dashboard senza sensori. |
| [docs/application-example.md](docs/application-example.md) | Schema dati, pin e dipendenze dell'applicazione di esempio inclusa. |

I moduli di trasporto e MQTT del client e del server restano distinti perché le versioni originali differiscono. La dashboard inclusa visualizza un **formato JSON di esempio** descritto nella guida applicativa; altri progetti possono riutilizzare i moduli MQTT con i propri payload e topic, adattando la visualizzazione se necessario.

## Requisiti

Per provare **broker + dashboard** bastano un ESP8266, [Arduino IDE e il core ESP8266](https://arduino-esp8266.readthedocs.io/en/latest/installing.html), la libreria [PubSubClient](https://github.com/knolleary/pubsubclient), Python 3 e un broker [Eclipse Mosquitto](https://mosquitto.org/download/) accessibile dalla LAN. ESP8266WiFi ed ESP8266WebServer sono inclusi nel core.

Per usare il **bridge con una STM32** servono anche la scheda, l'ambiente ChibiOS e un ESP8266 dedicato per ogni STM32. I Makefile esportati mantengono i percorsi del progetto hardware di origine: questa repository da sola non contiene ChibiOS e i driver dei sensori, quindi non costituisce una build STM32 autonoma. L'integrazione su un'altra MCU o RTOS richiede un adattamento del trasporto UART e dell'HAL.

## 1. Configurare rete, broker e topic

~~~sh
git clone https://github.com/Sal-zip/ESP8266-mqtt-demo.git
cd ESP8266-mqtt-demo
cp config.example.json config.json
~~~

Modificare **config.json**:

- Inserire SSID e password Wi-Fi della rete usata dagli ESP8266.
- Impostare in **broker.host** l'IP LAN o il nome DNS raggiungibile dagli ESP8266. Localhost e 127.0.0.1 indicano il dispositivo stesso, quindi non vanno usati per un broker su un altro computer.
- Impostare porta e, se richieste dal broker, credenziali MQTT.
- Scegliere i tre topic di pubblicazione: **telemetry**, **status** e **sos**. Le etichette identificano i tre flussi del codice fornito; i nomi dei topic sono liberi.
- Assegnare ID MQTT diversi a client STM32, server STM32 e dashboard. **devices.device_id** identifica il dispositivo nei payload JSON dell'applicazione di esempio.

Generare gli header usati dai sorgenti:

~~~sh
python3 tools/configure.py
~~~

Il comando crea:

- communication/client/include/app_config.h
- communication/server/include/app_config.h
- communication/server/esp8266/neapolis_sos_dashboard/demo_config.h

**config.json** e gli header generati sono esclusi da Git. Dopo una modifica, rieseguire il generatore e ricompilare i firmware coinvolti. Per più dispositivi publisher, generare una configurazione con Client ID MQTT e device_id distinti per ciascuno. Broker e nomi dei topic devono coincidere fra publisher e subscriber.

## 2. Avviare un broker di prova

Mosquitto 2.x avviato senza listener configurato può accettare solo connessioni locali; per raggiungerlo dall'ESP8266 serve un listener di rete ([documentazione ufficiale](https://mosquitto.org/documentation/migrating-to-2-0/)). Su una rete di laboratorio isolata, un file **mosquitto-demo.conf** minimo è:

~~~conf
listener 1883 0.0.0.0
allow_anonymous true
~~~

Avviare il broker con:

~~~sh
mosquitto -c mosquitto-demo.conf -v
~~~

Usare l'IP LAN del computer in config.json. Il listener anonimo di esempio serve per una prova locale; non esporlo a Internet. Se si usa l'[autenticazione Mosquitto](https://www.mosquitto.org/documentation/authentication-methods/), indicare username e password anche in config.json. Il codice usa MQTT su TCP senza TLS, normalmente sulla porta 1883.

## 3. Caricare e provare la dashboard

In Arduino IDE installare il core ESP8266 e PubSubClient, selezionare il modello di scheda e la porta corretti, quindi aprire [neapolis_sos_dashboard.ino](communication/server/esp8266/neapolis_sos_dashboard/neapolis_sos_dashboard.ino). L'header generato **demo_config.h** deve trovarsi nella stessa cartella dello sketch. Caricare il firmware e aprire il monitor seriale a **115200 baud**: quando il Wi-Fi è connesso, appare l'indirizzo da aprire nel browser.

Per inviare dati di esempio senza firmware STM32, dalla root della repository eseguire, sostituendo IP e topic se modificati:

~~~sh
mosquitto_pub -h <IP_DEL_BROKER> -p 1883 -t 'demo/esp8266/telemetry' -q 1 -f examples/telemetry.json
mosquitto_pub -h <IP_DEL_BROKER> -p 1883 -t 'demo/esp8266/alerts' -q 1 -f examples/sos.json
~~~

Nella pagina compariranno **device-01** e un evento di allarme. I JSON contengono valori fittizi. Per controllare il broker separatamente dalla pagina:

~~~sh
mosquitto_sub -h <IP_DEL_BROKER> -p 1883 -t 'demo/esp8266/#' -v
~~~

Se il broker richiede credenziali, aggiungere le opzioni di autenticazione previste dai client Mosquitto. Le API della dashboard sono disponibili a **/api/status** e **/api/messages** sull'IP dell'ESP8266. La pagina usa Leaflet e le tessere OpenStreetMap: la mappa richiede accesso Internet dal browser.

## 4. Usare il bridge nel proprio firmware

Caricare [neapolis_esp8266_tcp_bridge.ino](communication/server/esp8266/neapolis_esp8266_tcp_bridge/neapolis_esp8266_tcp_bridge.ino) su un ESP8266 **diverso da quello della dashboard**. Il bridge implementa il sottoinsieme di comandi AT usato dal firmware incluso. Riceve SSID, password e destinazione TCP dalla scheda principale via UART; non contiene credenziali proprie.

Collegare TX della scheda principale a RX dell'ESP8266, RX a TX e le masse insieme. UART0 dell'ESP8266 usa GPIO1/GPIO3 a **38400 baud**. Alimentazione e livelli logici devono essere adatti a **3,3 V**. Scollegare la UART della scheda principale se interferisce durante il caricamento dello sketch. I pin STM32 specifici dell'esempio sono nella [guida applicativa](docs/application-example.md).

Per integrare la comunicazione in un progetto ChibiOS:

1. Portare nel progetto i file **client/src/esp8266_transport.c**, **client/src/mqtt_client.c** e i rispettivi header. Configurare il SerialDriver collegato al bridge e una console separata.
2. Inizializzare transport e client MQTT come nell'[applicazione di esempio](communication/client/application/src/application.c). Chiamare prima **esp8266_transport_connect()**, poi **mqtt_client_open()**.
3. Pubblicare topic e payload con **mqtt_client_publish_qos1()**. Quando non ci sono messaggi, chiamare **mqtt_client_yield()** per elaborare il keep-alive. Dopo un errore, riconnettere e ritentare lo stesso messaggio finché arriva PUBACK.
4. Per ricevere, usare il codice in [server/src/](communication/server/src/) e la callback in [server/main.c](communication/server/main.c) come riferimento. Se si usa la dashboard, la si può tenere indipendente dal server STM32.

Su altre piattaforme occorre implementare l'interfaccia di **esp8266_transport.h** usando UART e temporizzazione disponibili. Il layer MQTT lavora su un flusso di byte TCP trasparente; la configurazione JSON evita modifiche a Wi-Fi, host e topic, ma non esegue il porting dell'HAL.

## Contratto MQTT e limiti

Il publisher STM32 fornito usa MQTT 3.1.1 e **QoS 1**. Dopo un PUBACK mancante ritenta lo stesso messaggio; QoS 1 consente duplicati, quindi un'applicazione che richiede unicità dovrebbe deduplicare tramite eventId. La coda applicativa del client è in **RAM**: un riavvio prima del PUBACK può perdere un evento. Anche la dashboard conserva soltanto gli ultimi **20 messaggi in RAM**. Il server STM32 sottoscrive tre topic esatti configurati dal generatore.

La dashboard inclusa interpreta il JSON dell'[esempio applicativo](docs/application-example.md): richiede almeno schemaVersion 1 e un deviceId non vuoto, e usa GPS, PPG e MQ2 per la vista dettagliata. Chi usa payload diversi può riutilizzare il trasporto e il broker, ma deve adattare la pagina web. La dashboard è uno sketch HTTP sull'ESP8266; non usa un backend web separato.

## Problemi comuni

| Sintomo | Controllo |
| --- | --- |
| Il generatore rifiuta config.json | Sostituire i placeholder; usare Client ID e topic distinti. |
| Wi-Fi connesso, MQTT disconnesso | Verificare IP LAN del broker, listener, firewall, porta e credenziali. |
| Il broker riceve messaggi, la pagina è vuota | Controllare che topic, schemaVersion e deviceId coincidano con l'esempio; aprire /api/status e /api/messages. |
| Mappa assente | Verificare l'accesso del browser a Leaflet e OpenStreetMap. |
| Bridge senza risposta | Controllare firmware caricato, UART a 38400, TX/RX incrociati, massa comune e alimentazione. |
| Duplicati dopo una disconnessione | Previsti da QoS 1; deduplicare con eventId se necessario. |

## Provenienza

Il codice della cartella **communication/** proviene dal [prototipo di riferimento, commit d6e0cdd](https://github.com/Sal-zip/Progetto-Neapolis-Innovation-2026/tree/d6e0cdd/Rescue%20Vest%20-%20Prototipo/comunication). La logica del firmware già verificato sul progetto originale resta invariata; questa repository sposta Wi-Fi, broker, topic e ID in una configurazione generata. Le caratteristiche specifiche del caso d'uso originale sono documentate a parte nella [guida applicativa](docs/application-example.md).
