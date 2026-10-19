@echo off
chcp 65001 > nul
echo ========================================================
echo        Очистка временного кеша браузера
echo        (Сессия и вход на hh.ru сохраняются!)
echo ========================================================
echo.

set "PROFILE_DIR=%~dp0browser_profile"

if exist "%PROFILE_DIR%\Default\Cache" (
    rmdir /s /q "%PROFILE_DIR%\Default\Cache" >nul 2>&1
    echo [✓] Очищен HTTP Cache
)
if exist "%PROFILE_DIR%\Default\Code Cache" (
    rmdir /s /q "%PROFILE_DIR%\Default\Code Cache" >nul 2>&1
    echo [✓] Очищен V8 Code Cache
)
if exist "%PROFILE_DIR%\Default\GPUCache" (
    rmdir /s /q "%PROFILE_DIR%\Default\GPUCache" >nul 2>&1
    echo [✓] Очищен GPU Cache
)
if exist "%PROFILE_DIR%\GrShaderCache" (
    rmdir /s /q "%PROFILE_DIR%\GrShaderCache" >nul 2>&1
    echo [✓] Очищен GrShaderCache
)
if exist "%PROFILE_DIR%\ShaderCache" (
    rmdir /s /q "%PROFILE_DIR%\ShaderCache" >nul 2>&1
    echo [✓] Очищен ShaderCache
)
if exist "%PROFILE_DIR%\Crashpad" (
    rmdir /s /q "%PROFILE_DIR%\Crashpad" >nul 2>&1
    echo [✓] Очищен Crashpad
)

echo.
echo Кеш успешно очищен! Папка профиля оптимизирована.
echo.
pause
