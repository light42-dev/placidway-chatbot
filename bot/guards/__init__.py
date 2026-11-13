"""Checks done in code, before and after the model, for rules too important to leave to a prompt.

Each module covers one risk:

- crisis      a user who may be at risk gets support and a crisis line, never prices
- abuse       flooding, bulk extraction, rapid-fire requests
- injection   attempts to override the rules, leak them or slip in prices
- documents   requests for letters, invoices, reviews, or confirmation of a patient's treatment
- prices      amounts no page lists, converted currencies, dictated wording
- figures     any other number (a duration, a percentage) the model was not shown
- contacts    foreign links, phone numbers, emails, bank details
- pointers    a free quote when the pages lack the answer; a doctor for health questions
"""
