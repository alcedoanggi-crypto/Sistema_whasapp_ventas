-- Ejecutar como superusuario:  psql -U postgres -f scripts/crear_bd.sql
CREATE ROLE wa_app LOGIN PASSWORD 'wa_pass';
CREATE DATABASE whatsapp_ventas OWNER wa_app ENCODING 'UTF8';
-- Base para los tests de integración
CREATE DATABASE whatsapp_ventas_test OWNER wa_app ENCODING 'UTF8';
