# Initial Balances (საწყისი ნაშთები)

This module allows importing initial balances from Excel files into Odoo journal entries.

## Features

- Import initial balances from Excel files
- Automatic debit/credit determination based on account codes
- Partner matching by VAT or name
- Creates a single journal entry with all imported lines

## Excel File Format

The Excel file should have the following structure:

| Column | Description | Required |
|--------|-------------|----------|
| A | Account Code | Yes |
| B | Identification ID (VAT) | No |
| C | Partner Name | No |
| D | Amount | Yes |

**Note:** Data should start from row 2 (row 1 is for headers)

## Business Rules

### Debit/Credit Logic
- Accounts starting with **"14"** → Amount goes to **Debit**
- Accounts starting with **"9"** → Amount goes to **Credit**
- Other accounts → Positive amounts to Debit, negative to Credit

### Partner Matching
1. First, searches by VAT (column B)
   - If VAT contains ".", only the part before "." is used
   - VAT is normalized to 11 digits
2. If not found by VAT, searches by name (column C)
3. If no partner found, the line is created without a partner

## Usage

1. Go to **Accounting** → **Accounting** → **საწყისი ნაშთები**
2. Upload your Excel file
3. Click **Import**

**Note:** The journal entry is automatically created with:
- **Date:** December 31, 2025
- **Journal:** Opening Entries Journal (must exist)

The module will:
- Validate the Excel file
- Search for accounts and partners
- Create a journal entry with all the lines
- Show errors if any accounts are not found or data is invalid

## Installation

1. Copy the module to your Odoo addons directory
2. Update the app list
3. Install "Initial Balances (საწყისი ნაშთები)"

## Dependencies

- account

## Version

18.0.1.0.0

