- The external stock inventory are linked to its created stock quants to see the imported quantities. However, that quants can be changed in the future, and it can cause some traceability problems:
  - The external stock inventory can show that it applied a different stock quantity. It is recomended to create another related model or field to see the imported data.
  - The manual stock quant changes, that are applied after an external stock inventory, creates stock moves that are still linked to the external stock inventory, when they must not.

- Filters can be used to avoid applying stock inventory adjustments to products whose quantity has not been changed. Or, at least, to not show stock moves without changes.
