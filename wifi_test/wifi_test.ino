#include <WiFi.h>

const char *ssid = "IRON MAN";
const char *password = "America1972";
WiFiServer server(80);

#define LED_PIN 2 // D2

void conectarWiFi() {
  while (WiFi.status() != WL_CONNECTED) {
    if(WiFi.status() != WL_CONNECTED){
      WiFi.begin(ssid, password);
    }else{
      break;
    }
    digitalWrite(LED_PIN, HIGH);
    delay(300);
    digitalWrite(LED_PIN, LOW);
    delay(300);
    
  }
  //WiFi.config(local_IP, gateway, subnet);
  digitalWrite(LED_PIN, LOW);
  delay(100);
  // Aquí podrías agregar un mensaje para indicar que se ha conectado a la red WiFi
  Serial.println("Conectado a la red WiFi");
  server.begin();
}
void setup() {
  Serial.begin(115200);
  delay(1000);  
  pinMode(LED_PIN, OUTPUT);
  conectarWiFi();
}

void loop() {
  delay(1000);
  if (WiFi.status() != WL_CONNECTED) {
    // Intentar reconectar
    conectarWiFi();
  }
  
  Serial.println(WiFi.localIP());
  WiFiClient client = server.available();
  if (client) {
    Serial.println("$$");
    digitalWrite(LED_PIN, HIGH);
    while (client.connected()) {
      if (client.available() > 0) {
        String incomingString = client.readStringUntil('\n');
        Serial.println(incomingString);
      }
      if (Serial.available() > 0) {
        String incomingStrings = Serial.readStringUntil('\n');
        client.println(incomingStrings);
      }
    }
    digitalWrite(LED_PIN, LOW);
    Serial.println("$X");
  }
}