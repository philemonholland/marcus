void setup() {
  Serial.begin(115200);
  Serial1.begin(115200);
  while (!Serial);         // Attendre que le port série soit prêt
  delay(1000);              // Laisser le temps à la connexion de s'établir
  Serial.println("READY");  // Informer le PC que l'Arduino est prêt
}

void loop() {
  if (Serial.available()) {
    char received = Serial.read();

    if (received == '1')
    {
      Serial1.println("Caractère 1 reçu du PC");
      digitalWrite(LED_BUILTIN, HIGH);
      Serial.println("ACK1");
    } 
    else if (received == '0') 
    { 
      Serial1.println("Caractère 0 reçu du PC");
      digitalWrite(LED_BUILTIN, LOW);
      Serial.println("ACK0");
    } 
    
  }
}
