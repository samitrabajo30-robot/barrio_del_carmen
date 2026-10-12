# Barrio Del Carmen · Río Gallegos

Sitio público adaptable a celulares y computadoras, más un panel privado para que una persona autorizada actualice textos e imagen y gestione los avisos vecinales.

## Qué puede hacer cada parte

- **Página pública (`index.html`):** presenta el barrio; la queja vecinal se envía en privado a la Junta Vecinal cuando el backend está configurado. Los eventos siguen siendo una vista previa.
- **Panel privado (`admin.html`):** iniciar sesión, editar presentación, historia, un texto adicional y la imagen, ver quejas, filtrarlas por fecha/tema/zona/estado, cambiar su estado y descargar el resultado filtrado en Excel (`.xlsx`).
- **Base de datos:** conserva textos y quejas. Los visitantes pueden enviar quejas, pero solo la cuenta autorizada puede leerlas o cambiar su seguimiento.

El panel no tiene una clave fija ni un acceso abierto. La cuenta se crea y autoriza en el servicio de backend.

## Configuración para activar el acceso real

La página requiere conexión a internet y publicarse bajo una dirección HTTPS. Abrir archivos locales con `file://` sirve para mirar el diseño, pero no para operar la base de datos.

1. Crear un proyecto en **Supabase**.
2. En el panel de Supabase, abrir **SQL Editor**, pegar el contenido de `setup_supabase.sql` y ejecutarlo. Esto crea las tablas, permisos privados, y el almacenamiento de imágenes.
3. Crear la cuenta del tercero en **Authentication → Users**. Elegí una contraseña segura y entregásela por un canal privado.
4. Copiar el UUID de esa cuenta y autorizarla desde el SQL Editor ejecutando:

   ```sql
   insert into public.admins (user_id) values ('PEGAR-EL-UUID-DE-LA-CUENTA');
   ```

5. En la configuración de API del proyecto, copiar la **Project URL** y la clave pública **anon/publishable**. Pegarlas en `config.js`:

   ```js
   window.BARRIO_CONFIG = {
     supabaseUrl: 'https://TU-PROYECTO.supabase.co',
     supabaseAnonKey: 'TU-CLAVE-PUBLICA',
   };
   ```

   La clave pública está pensada para estar en el sitio: los permisos de base de datos controlan lo que puede hacer cada visitante. **Nunca copies la clave `service_role` en `config.js` ni en la página.**

6. Publicar todos los archivos de esta carpeta en un alojamiento web con HTTPS. La persona administradora entra en `https://tu-dominio/admin.html`; el público usa `https://tu-dominio/`.

## Uso del panel

En **Contenido de la página**, editar presentación e historia y, si corresponde, elegir una imagen JPG, PNG o WEBP de hasta 5 MB. En **Avisos y quejas**, aplicar filtros; la planilla descarga exactamente los resultados filtrados, con fecha y horario del problema, zona, tema, descripción, fecha y horario de envío y estado. El archivo no incluye nombre ni teléfono porque el formulario no los solicita.

Para dar acceso a otra persona, crear una cuenta de autenticación y agregar su UUID a `public.admins`. Para quitarle el acceso, eliminar su fila de esa tabla y deshabilitar o borrar su usuario.

## Seguridad y puesta en marcha

- Las políticas RLS de `setup_supabase.sql` impiden la lectura pública de quejas y restringen la administración a usuarios autorizados.
- La imagen de portada se guarda en un bucket público para que cualquiera pueda verla; no subas imágenes privadas o sin autorización.
- El formulario incluye validación de campos y una trampa sencilla para bots. Antes de difundirlo masivamente, conviene agregar CAPTCHA o un límite de envíos en servidor para reducir spam.
- Definir quién responderá los avisos, por cuánto tiempo se conservarán y cómo se gestionarán copias de seguridad. No pedir ni incluir datos personales sensibles.
- El panel y el envío de quejas requieren los scripts de Supabase/Excel desde CDN; la página debe estar alojada y el navegador conectado a internet.

## Archivos principales

- `index.html`, `styles.css`, `app.js`: sitio público.
- `admin.html`, `admin.css`, `admin.js`: panel de administración.
- `config.js`: URL y clave pública del servicio.
- `setup_supabase.sql`: tablas, permisos y almacenamiento iniciales.
