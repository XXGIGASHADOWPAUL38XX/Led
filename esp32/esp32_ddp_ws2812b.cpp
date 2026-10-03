/*
  ESP32 DDP -> WS2812B
  --------------------
  Firmware minimal recevant directement un flux DDP RGB24.

  Fonctionnalites :
    - connexion Wi-Fi ;
    - reception DDP sur UDP 4048 ;
    - gestion des paquets fragmentes par offset ;
    - affichage lors du flag DDP PUSH ;
    - sortie WS2812B avec Adafruit_NeoPixel ;
    - correction gamma optionnelle ;
    - balance des blancs RGB configurable ;
    - aucun dithering temporel ;
    - aucune limitation logicielle de luminosite.

  Dependances Arduino :
    - carte "esp32 by Espressif Systems"
    - bibliotheque "Adafruit NeoPixel"

  ATTENTION ELECTRIQUE :
    - ne pas alimenter 300 LED depuis le 5 V de l'ESP32 ;
    - utiliser une alimentation 5 V dimensionnee pour le ruban ;
    - relier la masse de l'alimentation LED a la masse de l'ESP32 ;
    - un convertisseur logique 3,3 V -> 5 V est recommande ;
    - ajouter idealement une resistance de 220 a 470 ohms sur DATA.
*/

#include <Arduino.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include <Adafruit_NeoPixel.h>
#include <math.h>

// -----------------------------------------------------------------------------
// Configuration utilisateur
// -----------------------------------------------------------------------------

static const char* WIFI_SSID     = "Livebox-2B78";
static const char* WIFI_PASSWORD = "V2ZkF4CL94Zt5SsxRF";

// GPIO connecte a DIN du ruban.
static constexpr uint8_t LED_PIN = 5;

// Nombre de LED physiques.
static constexpr uint16_t LED_COUNT = 300;

// WS2812B est generalement GRB a 800 kHz.
static constexpr neoPixelType LED_TYPE = NEO_GRB + NEO_KHZ800;

// Port DDP utilise par le contrôleur ESP32.
static constexpr uint16_t DDP_PORT = 4048;

// Identifiant DDP attendu.
// 1 est l'identifiant d'affichage usuel.
// Mettre DDP_ACCEPT_ANY_ID a true pour ignorer cet identifiant.
static constexpr uint8_t DDP_DEVICE_ID = 1;
static constexpr bool DDP_ACCEPT_ANY_ID = true;

// Si le dernier paquet n'a pas le flag PUSH, afficher apres ce delai.
// Une valeur courte limite la latence tout en laissant arriver les fragments.
static constexpr uint32_t FRAME_FALLBACK_US = 2500;

// Taille maximale d'un datagramme UDP accepte.
// Un paquet Ethernet DDP classique tient normalement sous environ 1500 octets.
static constexpr size_t UDP_BUFFER_SIZE = 1536;

// -----------------------------------------------------------------------------
// Correction colorimetrique
// -----------------------------------------------------------------------------

static constexpr bool ENABLE_COLOR_CORRECTION = true;

// Gamma > 1 compresse les faibles valeurs PWM.
// Si votre logiciel emetteur applique deja un gamma, utilisez 1.0.
static constexpr float OUTPUT_GAMMA = 2.2f;

// Balance des blancs par canal.
// Diminuez un canal s'il parait trop fort.
static constexpr float RED_GAIN   = 1.00f;
static constexpr float GREEN_GAIN = 1.00f;
static constexpr float BLUE_GAIN  = 1.00f;

// Gain general fixe. 1.0 = aucune reduction.
static constexpr float MASTER_GAIN = 1.00f;

// Conserve au moins 1 pour toute entree non nulle.
// Laissez false pour une vraie courbe gamma.
static constexpr bool PRESERVE_NON_ZERO = false;

// -----------------------------------------------------------------------------
// Constantes DDP
// -----------------------------------------------------------------------------

static constexpr size_t DDP_HEADER_SIZE = 10;

// Byte 0 : version dans les deux bits de poids fort.
static constexpr uint8_t DDP_VERSION_MASK  = 0xC0;
static constexpr uint8_t DDP_VERSION_1     = 0x40;

// Byte 0 : flags.
static constexpr uint8_t DDP_FLAG_PUSH     = 0x01;
static constexpr uint8_t DDP_FLAG_QUERY    = 0x02;
static constexpr uint8_t DDP_FLAG_REPLY    = 0x04;

// Byte 2 : type de donnees.
// Le nibble bas 0x01 correspond au RGB 8 bits, soit 3 octets par pixel.
static constexpr uint8_t DDP_DATA_TYPE_MASK = 0x0F;
static constexpr uint8_t DDP_DATA_TYPE_RGB8 = 0x01;

// -----------------------------------------------------------------------------
// Etat global
// -----------------------------------------------------------------------------

WiFiUDP udp;
Adafruit_NeoPixel strip(LED_COUNT, LED_PIN, LED_TYPE);

// Buffer DDP en RGB logique, ordre R,G,B.
// Adafruit_NeoPixel se charge ensuite de produire l'ordre physique GRB.
static uint8_t rgbFrame[LED_COUNT * 3];
static uint8_t udpBuffer[UDP_BUFFER_SIZE];

static uint8_t correctionLutR[256];
static uint8_t correctionLutG[256];
static uint8_t correctionLutB[256];

static bool frameDirty = false;
static uint32_t lastDataMicros = 0;
static uint32_t packetCount = 0;
static uint32_t droppedPacketCount = 0;
static uint32_t shownFrameCount = 0;

// -----------------------------------------------------------------------------
// Correction colorimetrique
// -----------------------------------------------------------------------------

static uint8_t buildCorrectedValue(uint8_t input, float channelGain) {
  if (!ENABLE_COLOR_CORRECTION) {
    return input;
  }

  const float normalized = static_cast<float>(input) / 255.0f;
  const float gammaCorrected =
    (OUTPUT_GAMMA == 1.0f) ? normalized : powf(normalized, OUTPUT_GAMMA);

  float output = gammaCorrected * 255.0f * channelGain * MASTER_GAIN;

  if (output < 0.0f) output = 0.0f;
  if (output > 255.0f) output = 255.0f;

  uint8_t result = static_cast<uint8_t>(lroundf(output));

  if (PRESERVE_NON_ZERO && input > 0 && result == 0) {
    result = 1;
  }

  return result;
}

static void buildCorrectionLuts() {
  for (uint16_t value = 0; value < 256; ++value) {
    const uint8_t input = static_cast<uint8_t>(value);
    correctionLutR[value] = buildCorrectedValue(input, RED_GAIN);
    correctionLutG[value] = buildCorrectedValue(input, GREEN_GAIN);
    correctionLutB[value] = buildCorrectedValue(input, BLUE_GAIN);
  }

  Serial.printf(
    "Correction: %s, gamma=%.2f, gains RGB=%.3f/%.3f/%.3f, master=%.3f\n",
    ENABLE_COLOR_CORRECTION ? "activee" : "desactivee",
    OUTPUT_GAMMA,
    RED_GAIN,
    GREEN_GAIN,
    BLUE_GAIN,
    MASTER_GAIN
  );
}

// -----------------------------------------------------------------------------
// Utilitaires
// -----------------------------------------------------------------------------

static uint16_t readBigEndian16(const uint8_t* p) {
  return (static_cast<uint16_t>(p[0]) << 8)
       |  static_cast<uint16_t>(p[1]);
}

static uint32_t readBigEndian32(const uint8_t* p) {
  return (static_cast<uint32_t>(p[0]) << 24)
       | (static_cast<uint32_t>(p[1]) << 16)
       | (static_cast<uint32_t>(p[2]) << 8)
       |  static_cast<uint32_t>(p[3]);
}

static void clearStrip() {
  memset(rgbFrame, 0, sizeof(rgbFrame));
  strip.clear();
  strip.show();
  frameDirty = false;
}

static void showFrame() {
  // Conversion du framebuffer DDP RGB vers la representation de la bibliotheque.
  // Aucun gamma, aucune correction et aucun dithering ne sont appliques.
  for (uint16_t i = 0; i < LED_COUNT; ++i) {
    const size_t base = static_cast<size_t>(i) * 3;
    const uint8_t rawR = rgbFrame[base + 0];
    const uint8_t rawG = rgbFrame[base + 1];
    const uint8_t rawB = rgbFrame[base + 2];

    strip.setPixelColor(
      i,
      correctionLutR[rawR],
      correctionLutG[rawG],
      correctionLutB[rawB]
    );
  }

  strip.show();
  frameDirty = false;
  ++shownFrameCount;
}

// -----------------------------------------------------------------------------
// Decodage DDP
// -----------------------------------------------------------------------------

static bool processDdpPacket(const uint8_t* packet, size_t packetSize) {
  if (packetSize < DDP_HEADER_SIZE) {
    return false;
  }

  const uint8_t flags = packet[0];
  const uint8_t sequence = packet[1];
  const uint8_t dataType = packet[2];
  const uint8_t destinationId = packet[3];

  (void)sequence; // Disponible pour de futures statistiques/pertes de paquets.

  // DDP version 1.
  if ((flags & DDP_VERSION_MASK) != DDP_VERSION_1) {
    return false;
  }

  // Ce firmware est un recepteur de pixels, pas un serveur de requetes DDP.
  if ((flags & DDP_FLAG_QUERY) != 0 || (flags & DDP_FLAG_REPLY) != 0) {
    return false;
  }

  if (!DDP_ACCEPT_ANY_ID && destinationId != DDP_DEVICE_ID) {
    return false;
  }

  // RGB8/RGB24 uniquement.
  if ((dataType & DDP_DATA_TYPE_MASK) != DDP_DATA_TYPE_RGB8) {
    return false;
  }

  // Offset et longueur sont exprimes en octets dans l'espace de donnees DDP.
  const uint32_t dataOffset = readBigEndian32(packet + 4);
  const uint16_t declaredLength = readBigEndian16(packet + 8);

  const size_t availablePayload = packetSize - DDP_HEADER_SIZE;
  if (declaredLength == 0 || declaredLength > availablePayload) {
    return false;
  }

  const size_t frameSize = sizeof(rgbFrame);

  // Paquet entierement hors du framebuffer.
  if (dataOffset >= frameSize) {
    return false;
  }

  // Coupe proprement un paquet depassant la derniere LED.
  size_t copyLength = declaredLength;
  const size_t remainingFrameBytes = frameSize - static_cast<size_t>(dataOffset);
  if (copyLength > remainingFrameBytes) {
    copyLength = remainingFrameBytes;
  }

  memcpy(
    rgbFrame + static_cast<size_t>(dataOffset),
    packet + DDP_HEADER_SIZE,
    copyLength
  );

  frameDirty = true;
  lastDataMicros = micros();

  // Les émetteurs DDP placent PUSH sur le dernier fragment.
  if ((flags & DDP_FLAG_PUSH) != 0) {
    showFrame();
  }

  return true;
}

// -----------------------------------------------------------------------------
// Reseau
// -----------------------------------------------------------------------------

static void connectWifi() {
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false); // Reduit la latence et la variabilite des paquets DDP.
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  Serial.printf("Connexion Wi-Fi a %s", WIFI_SSID);

  while (WiFi.status() != WL_CONNECTED) {
    delay(250);
    Serial.print('.');
  }

  Serial.println();
  Serial.printf("Wi-Fi connecte. IP ESP32 : %s\n",
                WiFi.localIP().toString().c_str());
}

static void startDdpReceiver() {
  if (!udp.begin(DDP_PORT)) {
    Serial.printf("ERREUR : impossible d'ouvrir UDP %u\n", DDP_PORT);
    while (true) {
      delay(1000);
    }
  }

  Serial.printf("Reception DDP active sur UDP %u\n", DDP_PORT);
}

static void receiveUdpPackets() {
  // Vide tous les paquets deja presents dans la file UDP.
  // Cela evite de traiter un seul paquet par iteration et de creer de la latence.
  while (true) {
    const int packetSize = udp.parsePacket();
    if (packetSize <= 0) {
      break;
    }

    if (static_cast<size_t>(packetSize) > sizeof(udpBuffer)) {
      // Il faut tout de meme vider le datagramme.
      while (udp.available()) {
        udp.read();
      }
      ++droppedPacketCount;
      continue;
    }

    const int bytesRead = udp.read(udpBuffer, packetSize);
    if (bytesRead != packetSize) {
      ++droppedPacketCount;
      continue;
    }

    ++packetCount;

    if (!processDdpPacket(udpBuffer, static_cast<size_t>(bytesRead))) {
      ++droppedPacketCount;
    }
  }
}

// -----------------------------------------------------------------------------
// Arduino
// -----------------------------------------------------------------------------

void setup() {
  Serial.begin(115200);
  delay(200);

  Serial.println();
  Serial.println("ESP32 DDP -> WS2812B");

  buildCorrectionLuts();
  strip.begin();
  strip.setBrightness(255); // Pas de reduction logicielle de luminosite.
  clearStrip();

  connectWifi();
  startDdpReceiver();

  Serial.printf("LED : %u, GPIO : %u, framebuffer : %u octets\n",
                LED_COUNT,
                LED_PIN,
                static_cast<unsigned>(sizeof(rgbFrame)));
}

void loop() {
  receiveUdpPackets();

  // Secours pour les emetteurs qui omettent PUSH.
  // Le calcul avec soustraction unsigned reste correct au debordement de micros().
  if (frameDirty &&
      static_cast<uint32_t>(micros() - lastDataMicros) >= FRAME_FALLBACK_US) {
    showFrame();
  }

  // Statistiques non bloquantes toutes les cinq secondes.
  static uint32_t lastStatsMillis = 0;
  const uint32_t nowMillis = millis();

  if (nowMillis - lastStatsMillis >= 5000) {
    lastStatsMillis = nowMillis;

    Serial.printf(
      "DDP paquets=%lu, rejetes=%lu, frames=%lu, RSSI=%d dBm\n",
      static_cast<unsigned long>(packetCount),
      static_cast<unsigned long>(droppedPacketCount),
      static_cast<unsigned long>(shownFrameCount),
      WiFi.RSSI()
    );
  }

  // Aucun delay() : le recepteur doit relire UDP le plus rapidement possible.
}
