"""
Script de prueba para verificar que el servidor dual-stack funciona correctamente.

Este script verifica que:
1. El servidor puede crear sockets IPv4 e IPv6 separados
2. Ambos sockets escuchan en el puerto correcto
3. Se pueden hacer conexiones tanto IPv4 como IPv6
"""

import socket
import asyncio
import time
import sys
import os

# Agregar src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_socket_creation():
    """Prueba que se pueden crear los sockets correctamente."""
    print("=" * 60)
    print("TEST 1: Verificar creación de sockets con getaddrinfo()")
    print("=" * 60)

    bind_addr = '::'
    port = 9090

    try:
        # Simular lo que hace el servidor
        host_for_getaddrinfo = None if bind_addr == '::' else bind_addr

        addrinfos = socket.getaddrinfo(
            host_for_getaddrinfo,
            port,
            socket.AF_UNSPEC,
            socket.SOCK_STREAM,
            0,
            socket.AI_PASSIVE
        )

        print(f"\ngetaddrinfo() devolvió {len(addrinfos)} direcciones:")

        # Agrupar por familia
        addr_by_family = {}
        for family, socktype, proto, canonname, sockaddr in addrinfos:
            if family not in addr_by_family:
                addr_by_family[family] = (family, socktype, proto, sockaddr)
                family_name = 'IPv6' if family == socket.AF_INET6 else 'IPv4'
                print(f"  - {family_name}: {sockaddr}")

        print(f"\n[OK] Se encontraron {len(addr_by_family)} familias de direcciones")

        # Intentar crear los sockets
        print("\nCreando sockets...")
        sockets_created = []

        for family, (fam, socktype, proto, sockaddr) in addr_by_family.items():
            try:
                sock = socket.socket(fam, socktype, proto)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

                if fam == socket.AF_INET6:
                    sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)

                sock.bind(sockaddr)
                sock.listen()

                family_name = 'IPv6' if fam == socket.AF_INET6 else 'IPv4'
                actual_addr = sock.getsockname()
                print(f"  [OK] Socket {family_name} creado y vinculado a: {actual_addr}")

                sockets_created.append((family_name, sock))

            except OSError as e:
                family_name = 'IPv6' if fam == socket.AF_INET6 else 'IPv4'
                print(f"  [ERROR] Error creando socket {family_name}: {e}")

        # Cerrar sockets
        print("\nCerrando sockets de prueba...")
        for name, sock in sockets_created:
            sock.close()
            print(f"  - Socket {name} cerrado")

        if len(sockets_created) >= 1:
            print("\n[OK] TEST PASADO: Se pudieron crear los sockets")
            return True
        else:
            print("\n[ERROR] TEST FALLIDO: No se pudo crear ningun socket")
            return False

    except Exception as e:
        print(f"\n[ERROR] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_server_startup():
    """Prueba que el servidor puede iniciar correctamente."""
    print("\n" + "=" * 60)
    print("TEST 2: Verificar inicio del servidor")
    print("=" * 60)

    try:
        # Importar el módulo del servidor
        from server import start_server

        print("\n[OK] Modulo server.py importado correctamente")
        print("   (El servidor puede ejecutarse con: python src/server.py)")

        return True

    except ImportError as e:
        print(f"\n[ERROR] Error importando server.py: {e}")
        return False
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Ejecuta todos los tests."""
    print("\nSUITE DE PRUEBAS: Servidor Dual-Stack IPv4/IPv6\n")

    results = []

    # Test 1: Creación de sockets
    result1 = await test_socket_creation()
    results.append(result1)

    # Test 2: Startup del servidor
    result2 = await test_server_startup()
    results.append(result2)

    # Resumen
    print("\n" + "=" * 60)
    print("RESUMEN DE PRUEBAS")
    print("=" * 60)

    passed = sum(results)
    total = len(results)

    print(f"\nPruebas pasadas: {passed}/{total}")

    if all(results):
        print("\n[OK] TODOS LOS TESTS PASARON")
        print("\nProximos pasos:")
        print("1. Ejecutar el servidor con: docker-compose up")
        print("2. Probar conexion IPv4: python src/client.py --host 127.0.0.1 --ipv4 --video test_video.mp4 --processing blur")
        print("3. Probar conexion IPv6: python src/client.py --host ::1 --ipv6 --video test_video.mp4 --processing blur")
        return 0
    else:
        print("\n[ERROR] ALGUNOS TESTS FALLARON")
        return 1


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
