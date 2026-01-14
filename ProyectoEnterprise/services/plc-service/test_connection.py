import snap7
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("plc-forced-test")

PLC_IP = "192.168.0.11"
RACK = 0
SLOT = 1 # Tu CPU está en el Slot 1

def test_hard_connection():
    client = snap7.client.Client()
    try:
        logger.info(f"Intentando conexión forzada a {PLC_IP}...")
        
        # Tipo de conexión: 0x01 (PG), 0x02 (OP), 0x03 (S7 Basic)
        # Forzamos tipo PG que es el que usa TIA Portal
        client.set_connection_params(PLC_IP, 0x1112, 0x1113) # Parámetros bajos de S7-1500
        client.connect(PLC_IP, RACK, SLOT)
        
        if client.get_connected():
            logger.info("✅ ¡INCREÍBLE! Logramos conectar.")
            client.disconnect()
        else:
            # Si falla, probamos el método estándar pero con más tiempo
            logger.info("Reintentando método estándar...")
            client.connect(PLC_IP, RACK, SLOT)
            if client.get_connected():
                logger.info("✅ Conexión estándar lograda.")
                client.disconnect()
            else:
                logger.error("❌ Sigue fallando.")
                
    except Exception as e:
        logger.error(f"❌ Error: {e}")

if __name__ == "__main__":
    test_hard_connection()
