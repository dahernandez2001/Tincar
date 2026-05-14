# Tincar Mobile - Fase 1 (.NET MAUI + backend Flask actual)

## Objetivo

En esta fase, la app móvil consume el backend Flask existente sin migrar lógica de servidor.

Flujo implementado:
- Login con sesión Flask (`POST /login`) usando cookies
- Consultar `GET /api/parkings/active`
- Consultar `GET /api/reservations/active/driver`
- Consultar `GET /api/notifications`
- Mostrar información en 4 pantallas con MVVM básico
- Configuración Dev/Prod de URL desde archivos JSON

## Estructura creada

- `mobile/Tincar.Mobile.slnx`
- `mobile/Tincar.Mobile/`
- `mobile/Tincar.Mobile/Pages/LoginPage.xaml`
- `mobile/Tincar.Mobile/Pages/ParkingsPage.xaml`
- `mobile/Tincar.Mobile/Pages/ReservationsPage.xaml`
- `mobile/Tincar.Mobile/Pages/NotificationsPage.xaml`
- `mobile/Tincar.Mobile/ViewModels/*`
- `mobile/Tincar.Mobile/Services/TincarApiClient.cs`
- `mobile/Tincar.Mobile/Services/EnvironmentConfigService.cs`
- `mobile/Tincar.Mobile/Resources/Raw/appsettings.Development.json`
- `mobile/Tincar.Mobile/Resources/Raw/appsettings.Production.json`

## Requisitos para ejecutar

1. .NET SDK 10+
2. Workload MAUI Android:
   - `dotnet workload install maui-android`
3. Android SDK instalado y configurado
   - Debe existir variable `ANDROID_SDK_ROOT` (o configurar `AndroidSdkDirectory`)

## Levantar backend Flask (proyecto actual)

Desde la raíz del repo:

```bash
pip install -r requirements.txt
python app.py
```

Asumiendo backend en `http://localhost:5000`.

## Conectividad desde emulador Android

En Android Emulator, `localhost` apunta al mismo emulador, no al host.
Usa:

- `http://10.0.2.2:5000`

Ese valor ya va por defecto en la app.

## Ejecutar app móvil

```bash
dotnet restore mobile/Tincar.Mobile/Tincar.Mobile.csproj
dotnet build mobile/Tincar.Mobile/Tincar.Mobile.csproj -f net10.0-android
```

Si quieres desplegar en emulador/dispositivo desde CLI, necesitas Android SDK + emulador/dispositivo configurado.

## Próximo paso sugerido

- Añadir creación/cancelación de reservas desde móvil
- Añadir indicador global de sesión autenticada
- Agregar manejo de errores de red por código (401, 403, 500)
