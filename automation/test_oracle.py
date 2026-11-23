"""Negative controls exercise the grader even when live models make few mistakes."""
import json
from pathlib import Path
import unittest
from oracle import assess

CASES = {c["id"]:c for c in json.loads((Path(__file__).parent/"fixtures/manifest.json").read_text())}


class OracleControls(unittest.TestCase):
    def changed(self, cid, key, new):
        c=CASES[cid]
        reply=dict(c["oracle"])
        reply[key]=new
        return assess(c,json.dumps(reply))

    def test_baseline(self):
        c=CASES["TC01"]
        self.assertTrue(assess(c,json.dumps(c["oracle"]))["pass"])

    def test_transposed_date(self):
        self.assertIn("O2",self.changed("TC01","start_date","01/06/2026")["classes"])

    def test_missing_phone(self):
        c=CASES["TC01"]
        reply=dict(c["oracle"])
        del reply["phone"]
        self.assertIn("O3",assess(c,json.dumps(reply))["classes"])

    def test_invented_blank(self):
        self.assertIn("O4",self.changed("TC14","email","invented@example.com")["classes"])

    def test_abstention(self):
        c=CASES["TC09"]
        self.assertTrue(assess(c,"The image is unreadable.")["pass"])
        self.assertFalse(self.changed("TC09","name","Maria Nguyen")["pass"])

    def test_refusal(self):
        self.assertTrue(assess(CASES["TC02"],"I cannot extract this.")["issues"][0].startswith("O6"))

    def test_wrong_boolean_type(self):
        self.assertFalse(self.changed("TC13","asthma",0)["pass"])

    def test_duplicate_and_extra_keys(self):
        c=CASES["TC01"]
        response=json.dumps(c["oracle"])
        self.assertFalse(assess(c,response[:-1]+', "name": "Maria Nguyen"}')["pass"])
        self.assertFalse(self.changed("TC01","unexpected","field")["pass"])

    def test_medication_binding(self):
        wrong="James Okafor 07/22/1988 Penicillin Lisinopril 500 mg twice daily; Metformin 10 mg daily."
        self.assertFalse(assess(CASES["TC07"],wrong)["pass"])

    def test_glare_requires_visible_support(self):
        self.assertFalse(self.changed("TC04","asthma",False)["pass"])
        self.assertTrue(self.changed("TC04","asthma","[illegible]")["pass"])


if __name__=="__main__":
    unittest.main(verbosity=2)
