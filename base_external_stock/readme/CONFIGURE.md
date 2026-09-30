To configure the external inventory adjustments:

1. Go to "Inventory / Configuration / External Inventory Adjustments Config"
2. Create a record
3. Select the supplier
4. Select the stock location where its stock will be recorded (Back in the external inventory adjustments configuration). The stock in this
   locations should not compute as available stock for the products. We recommend an
   internal stock location whithout parent and childrens, with no relation with the main
   warehouses (you can create a new warehouse for this).
5. Review or fill the other configuration fields if needed. They configure technical elements of the call, point your cursor over them to see their help text. Keep their default values if you do not underestand them.
6. Install a module that extends with a concrete implementation. You can also put the configuration record in test mode, which contains a simple testing implementation of this module's funcionality.


IMPORTANT: The modules that inherit base_external_stock should implement the __get_external_stock_data_batch_enabled() and _test_connection() functions.