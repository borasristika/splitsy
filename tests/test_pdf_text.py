import unittest
from src import pdf_text


class TestPdfText(unittest.TestCase):
    def test_extract_text_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            pdf_text.extract_text("/no/such/file.pdf")

    def test_module_exposes_extract_text(self):
        self.assertTrue(callable(pdf_text.extract_text))


if __name__ == "__main__":
    unittest.main()
