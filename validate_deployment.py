#!/usr/bin/env python3
"""
Script de validación completa para deployment en DigitalOcean
"""
import os
import sys
import subprocess
import importlib.util

def test_wsgi_import():
    """Test de importación del módulo wsgi"""
    print("\n🔍 Test 1: Importación del módulo wsgi")
    try:
        import wsgi
        print(f"✅ wsgi.py importado exitosamente")
        print(f"✅ application = {wsgi.application}")
        print(f"✅ type = {type(wsgi.application)}")
        
        # Verificar que es una aplicación Flask válida
        if hasattr(wsgi.application, 'wsgi_app'):
            print("✅ Es una aplicación Flask válida")
            return True
        else:
            print("❌ No es una aplicación Flask válida")
            return False
            
    except Exception as e:
        print(f"❌ Error importando wsgi: {e}")
        return False

def test_gunicorn_config():
    """Test de configuración de Gunicorn"""
    print("\n🔍 Test 2: Configuración de Gunicorn")
    try:
        result = subprocess.run(
            ['gunicorn', '--check-config', 'wsgi:application'],
            capture_output=True, text=True, timeout=30
        )
        
        if result.returncode == 0:
            print("✅ Gunicorn puede encontrar la aplicación")
            return True
        else:
            print(f"❌ Error en Gunicorn: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Timeout en test de Gunicorn")
        return False
    except Exception as e:
        print(f"❌ Error ejecutando Gunicorn: {e}")
        return False

def test_main_import():
    """Test de importación del archivo main.py alternativo"""
    print("\n🔍 Test 3: Archivo main.py alternativo")
    try:
        import main
        print(f"✅ main.py importado exitosamente")
        print(f"✅ main.app = {main.app}")
        return True
    except Exception as e:
        print(f"❌ Error importando main.py: {e}")
        return False

def test_files_exist():
    """Test de existencia de archivos críticos"""
    print("\n🔍 Test 4: Archivos requeridos")
    files = ['wsgi.py', 'Procfile', 'app.yaml', 'requirements.txt', 'main.py']
    all_exist = True
    
    for file in files:
        if os.path.exists(file):
            print(f"✅ {file} existe")
        else:
            print(f"❌ {file} NO existe")
            all_exist = False
    
    return all_exist

def test_procfile_content():
    """Test del contenido del Procfile"""
    print("\n🔍 Test 5: Contenido del Procfile")
    try:
        with open('Procfile', 'r') as f:
            content = f.read().strip()
        
        expected = "web: gunicorn wsgi:application"
        if content == expected:
            print(f"✅ Procfile correcto: {content}")
            return True
        else:
            print(f"❌ Procfile incorrecto. Esperado: {expected}, Actual: {content}")
            return False
            
    except Exception as e:
        print(f"❌ Error leyendo Procfile: {e}")
        return False

def test_app_yaml_content():
    """Test del contenido del app.yaml"""
    print("\n🔍 Test 6: Contenido del app.yaml")
    try:
        with open('app.yaml', 'r') as f:
            content = f.read()
        
        if 'wsgi:application' in content:
            print("✅ app.yaml contiene referencia correcta a wsgi:application")
            return True
        else:
            print("❌ app.yaml NO contiene referencia a wsgi:application")
            return False
            
    except Exception as e:
        print(f"❌ Error leyendo app.yaml: {e}")
        return False

def main():
    """Ejecutar todos los tests"""
    print("🚀 VALIDACIÓN COMPLETA PARA DIGITALOCEAN APP PLATFORM")
    print("=" * 60)
    
    tests = [
        test_files_exist,
        test_wsgi_import,
        test_gunicorn_config,
        test_main_import,
        test_procfile_content,
        test_app_yaml_content
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Error en test: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print("📊 RESUMEN DE VALIDACIÓN")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"🎉 TODOS LOS TESTS PASARON ({passed}/{total})")
        print("🚀 ¡El deployment debería funcionar correctamente!")
        return True
    else:
        print(f"⚠️ ALGUNOS TESTS FALLARON ({passed}/{total})")
        print("🔧 Revisa los errores antes de hacer deployment")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 
"""
Script de validación completa para deployment en DigitalOcean
"""
import os
import sys
import subprocess
import importlib.util

def test_wsgi_import():
    """Test de importación del módulo wsgi"""
    print("\n🔍 Test 1: Importación del módulo wsgi")
    try:
        import wsgi
        print(f"✅ wsgi.py importado exitosamente")
        print(f"✅ application = {wsgi.application}")
        print(f"✅ type = {type(wsgi.application)}")
        
        # Verificar que es una aplicación Flask válida
        if hasattr(wsgi.application, 'wsgi_app'):
            print("✅ Es una aplicación Flask válida")
            return True
        else:
            print("❌ No es una aplicación Flask válida")
            return False
            
    except Exception as e:
        print(f"❌ Error importando wsgi: {e}")
        return False

def test_gunicorn_config():
    """Test de configuración de Gunicorn"""
    print("\n🔍 Test 2: Configuración de Gunicorn")
    try:
        result = subprocess.run(
            ['gunicorn', '--check-config', 'wsgi:application'],
            capture_output=True, text=True, timeout=30
        )
        
        if result.returncode == 0:
            print("✅ Gunicorn puede encontrar la aplicación")
            return True
        else:
            print(f"❌ Error en Gunicorn: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Timeout en test de Gunicorn")
        return False
    except Exception as e:
        print(f"❌ Error ejecutando Gunicorn: {e}")
        return False

def test_main_import():
    """Test de importación del archivo main.py alternativo"""
    print("\n🔍 Test 3: Archivo main.py alternativo")
    try:
        import main
        print(f"✅ main.py importado exitosamente")
        print(f"✅ main.app = {main.app}")
        return True
    except Exception as e:
        print(f"❌ Error importando main.py: {e}")
        return False

def test_files_exist():
    """Test de existencia de archivos críticos"""
    print("\n🔍 Test 4: Archivos requeridos")
    files = ['wsgi.py', 'Procfile', 'app.yaml', 'requirements.txt', 'main.py']
    all_exist = True
    
    for file in files:
        if os.path.exists(file):
            print(f"✅ {file} existe")
        else:
            print(f"❌ {file} NO existe")
            all_exist = False
    
    return all_exist

def test_procfile_content():
    """Test del contenido del Procfile"""
    print("\n🔍 Test 5: Contenido del Procfile")
    try:
        with open('Procfile', 'r') as f:
            content = f.read().strip()
        
        expected = "web: gunicorn wsgi:application"
        if content == expected:
            print(f"✅ Procfile correcto: {content}")
            return True
        else:
            print(f"❌ Procfile incorrecto. Esperado: {expected}, Actual: {content}")
            return False
            
    except Exception as e:
        print(f"❌ Error leyendo Procfile: {e}")
        return False

def test_app_yaml_content():
    """Test del contenido del app.yaml"""
    print("\n🔍 Test 6: Contenido del app.yaml")
    try:
        with open('app.yaml', 'r') as f:
            content = f.read()
        
        if 'wsgi:application' in content:
            print("✅ app.yaml contiene referencia correcta a wsgi:application")
            return True
        else:
            print("❌ app.yaml NO contiene referencia a wsgi:application")
            return False
            
    except Exception as e:
        print(f"❌ Error leyendo app.yaml: {e}")
        return False

def main():
    """Ejecutar todos los tests"""
    print("🚀 VALIDACIÓN COMPLETA PARA DIGITALOCEAN APP PLATFORM")
    print("=" * 60)
    
    tests = [
        test_files_exist,
        test_wsgi_import,
        test_gunicorn_config,
        test_main_import,
        test_procfile_content,
        test_app_yaml_content
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Error en test: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print("📊 RESUMEN DE VALIDACIÓN")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"🎉 TODOS LOS TESTS PASARON ({passed}/{total})")
        print("🚀 ¡El deployment debería funcionar correctamente!")
        return True
    else:
        print(f"⚠️ ALGUNOS TESTS FALLARON ({passed}/{total})")
        print("🔧 Revisa los errores antes de hacer deployment")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 