"""Unit tests for calculator module."""

import unittest
from calculator.calculator import (
    add, subtract, multiply, divide, power, modulo, calculate,
    CalculatorError
)


class TestCalculatorOperations(unittest.TestCase):
    """Test case for calculator operations."""
    
    def test_add_positive(self):
        """Test addition of positive numbers."""
        self.assertEqual(add(2, 3), 5)
        self.assertEqual(add(10, 20), 30)
    
    def test_add_negative(self):
        """Test addition with negative numbers."""
        self.assertEqual(add(-5, -3), -8)
        self.assertEqual(add(-5, 3), -2)
    
    def test_add_float(self):
        """Test addition with floats."""
        self.assertAlmostEqual(add(1.5, 2.5), 4.0)
    
    def test_subtract(self):
        """Test subtraction."""
        self.assertEqual(subtract(10, 5), 5)
        self.assertEqual(subtract(5, 10), -5)
        self.assertEqual(subtract(-5, -3), -2)
    
    def test_multiply(self):
        """Test multiplication."""
        self.assertEqual(multiply(3, 4), 12)
        self.assertEqual(multiply(-2, 3), -6)
        self.assertEqual(multiply(-2, -3), 6)
    
    def test_divide(self):
        """Test division."""
        self.assertEqual(divide(10, 2), 5)
        self.assertEqual(divide(10, 3), 3.3333333333333335)
        self.assertEqual(divide(-10, 2), -5)
    
    def test_divide_by_zero(self):
        """Test division by zero raises error."""
        with self.assertRaises(CalculatorError):
            divide(10, 0)
    
    def test_power(self):
        """Test power operation."""
        self.assertEqual(power(2, 3), 8)
        self.assertEqual(power(5, 2), 25)
        self.assertEqual(power(2, -1), 0.5)
    
    def test_modulo(self):
        """Test modulo operation."""
        self.assertEqual(modulo(10, 3), 1)
        self.assertEqual(modulo(15, 5), 0)
    
    def test_modulo_by_zero(self):
        """Test modulo by zero raises error."""
        with self.assertRaises(CalculatorError):
            modulo(10, 0)


class TestCalculateFunction(unittest.TestCase):
    """Test case for generic calculate function."""
    
    def test_calculate_add(self):
        """Test calculate with addition."""
        self.assertEqual(calculate(5, '+', 3), 8)
    
    def test_calculate_subtract(self):
        """Test calculate with subtraction."""
        self.assertEqual(calculate(5, '-', 3), 2)
    
    def test_calculate_multiply(self):
        """Test calculate with multiplication."""
        self.assertEqual(calculate(5, '*', 3), 15)
    
    def test_calculate_divide(self):
        """Test calculate with division."""
        result = calculate(6, '/', 2)
        self.assertAlmostEqual(result, 3.0)
    
    def test_calculate_power(self):
        """Test calculate with power."""
        self.assertEqual(calculate(2, '**', 3), 8)
    
    def test_calculate_modulo(self):
        """Test calculate with modulo."""
        self.assertEqual(calculate(10, '%', 3), 1)
    
    def test_calculate_invalid_operator(self):
        """Test calculate with invalid operator."""
        with self.assertRaises(CalculatorError):
            calculate(5, '@', 3)


if __name__ == '__main__':
    unittest.main()
