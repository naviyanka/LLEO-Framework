#!/usr/bin/env python3
import pytest
import sys
import os
from pathlib import Path
import argparse
import logging
from datetime import datetime

def setup_logging():
	"""Setup logging for test runs"""
	log_dir = Path('tests/logs')
	log_dir.mkdir(parents=True, exist_ok=True)
	
	log_file = log_dir / f'test_run_{datetime.now():%Y%m%d_%H%M%S}.log'
	
	logging.basicConfig(
		level=logging.INFO,
		format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
		handlers=[
			logging.FileHandler(log_file),
			logging.StreamHandler()
		]
	)
	return logging.getLogger('TestRunner')

def parse_args():
	"""Parse command line arguments"""
	parser = argparse.ArgumentParser(description='LLEO Test Runner')
	parser.add_argument(
		'--unit-only',
		action='store_true',
		help='Run only unit tests'
	)
	parser.add_argument(
		'--integration-only',
		action='store_true',
		help='Run only integration tests'
	)
	parser.add_argument(
		'--run-slow',
		action='store_true',
		help='Include slow tests'
	)
	parser.add_argument(
		'--coverage',
		action='store_true',
		help='Generate coverage report'
	)
	parser.add_argument(
		'--verbose', '-v',
		action='store_true',
		help='Verbose output'
	)
	return parser.parse_args()

def main():
	"""Main test runner function"""
	args = parse_args()
	logger = setup_logging()
	
	# Base pytest arguments
	pytest_args = ['-v'] if args.verbose else []
	
	# Add coverage if requested
	if args.coverage:
		pytest_args.extend([
			'--cov=core',
			'--cov-report=html',
			'--cov-report=term'
		])
	
	# Add slow tests if requested
	if args.run_slow:
		pytest_args.append('--run-slow')
	
	# Select test type
	if args.unit_only:
		pytest_args.append('tests/unit')
	elif args.integration_only:
		pytest_args.append('tests/integration')
	else:
		pytest_args.extend(['tests/unit', 'tests/integration'])
	
	logger.info(f"Running tests with arguments: {' '.join(pytest_args)}")
	
	try:
		result = pytest.main(pytest_args)
		
		if result == 0:
			logger.info("All tests passed successfully!")
		else:
			logger.error(f"Tests failed with exit code: {result}")
		
		if args.coverage:
			logger.info("Coverage report generated in htmlcov/index.html")
		
		sys.exit(result)
		
	except Exception as e:
		logger.error(f"Error running tests: {e}")
		sys.exit(1)

if __name__ == '__main__':
	main()