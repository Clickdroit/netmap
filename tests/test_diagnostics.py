import unittest
from backend.scanner.diagnostics import calculate_subnet_details, benchmark_dns_servers, send_wake_on_lan

class TestNetMapDiagnostics(unittest.TestCase):
    def test_subnet_calculator_valid(self):
        res = calculate_subnet_details("192.168.1.0/24")
        self.assertTrue(res["valid"])
        self.assertEqual(res["network_address"], "192.168.1.0")
        self.assertEqual(res["broadcast_address"], "192.168.1.255")
        self.assertEqual(res["netmask"], "255.255.255.0")
        self.assertEqual(res["usable_hosts"], 254)
        self.assertEqual(res["first_host"], "192.168.1.1")
        self.assertEqual(res["last_host"], "192.168.1.254")

    def test_subnet_calculator_invalid(self):
        res = calculate_subnet_details("999.999.999.999/99")
        self.assertFalse(res["valid"])
        self.assertIn("error", res)

    def test_wake_on_lan_validation(self):
        # Invalid MAC format
        res_bad = send_wake_on_lan("invalid-mac")
        self.assertFalse(res_bad["success"])

        # Valid MAC format test
        res_good = send_wake_on_lan("AA:BB:CC:DD:EE:FF")
        self.assertTrue(res_good["success"])

    def test_dns_benchmark_structure(self):
        res = benchmark_dns_servers()
        self.assertIsInstance(res, list)
        self.assertGreaterEqual(len(res), 1)
        self.assertIn("name", res[0])
        self.assertIn("ip", res[0])
        self.assertIn("status", res[0])

if __name__ == "__main__":
    unittest.main()
