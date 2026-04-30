# Barcode Location Prompt

## აღწერა (Description)

ეს მოდული უზრუნველყოფს, რომ Odoo 18-ის barcode სკანირების ინტერფეისში **ყველა ლოკაციის არჩევის საშუალება** გქონდეთ destination location-ისთვის შიდა გადაცემებისას (internal transfers).

**დამატებით:** 
- ავტომატურად ამატებს პროდუქტს `picking_type.x_studio_car_sawvav` ველიდან move line-ებში, როდესაც picking იქმნება ან იხსნება.
- ავტომატურად აყენებს `date_of_transfer` ველს მიმდინარე თარიღზე/დროზე, როდესაც picking იხსნება barcode ინტერფეისში.
- **რაოდენობის შეტანის ველი** - პირდაპირ შეიყვანეთ რაოდენობა ხელით, არა მხოლოდ +1 ღილაკით.

This module ensures that the Odoo 18 barcode scanning interface allows you to **select from ALL available locations** for destination in internal transfers, instead of being restricted to children of the picking type's default destination.

**Additionally:** 
- Automatically adds the product from `picking_type.x_studio_car_sawvav` field to move lines when a picking is created or opened.
- Automatically sets the `date_of_transfer` field to the current date/time when a picking is opened in the barcode interface.
- **Quantity Input Field** - Directly input quantity manually, not just using +1 button.

---

## პრობლემა რომელსაც წყვეტს (Problem It Solves)

**პრობლემა:** სტანდარტულად Odoo-ს barcode interface **ზღუდავს** destination location-ების არჩევანს მხოლოდ picking type-ის `default_location_dest_id`-ის children-ზე.

**გადაწყვეტა:** ეს მოდული **მოხსნის** ამ შეზღუდვას და აძლევს საშუალებას აირჩიოთ **ნებისმიერი** internal/transit location.

---

## როგორ მუშაობს (How It Works)

მოდული override-ს უკეთებს 4 ძირითად კომპონენტს:

### 1. **`stock.picking._get_stock_barcode_data()`**
   - აბრუნებს **ყველა internal/transit location-ს** barcode data-ში
   - ცვლის `destination_locations_ids` და `source_location_ids` keys-ს
   - **ავტომატურად ამატებს პროდუქტს** `picking_type.x_studio_car_sawvav`-დან
   - **ავტომატურად აყენებს** `date_of_transfer` ველს მიმდინარე თარიღზე

### 2. **`stock.picking._set_date_of_transfer()`** 🆕
   - ამოწმებს არსებობს თუ არა `date_of_transfer` ველი
   - თუ ველი **ცარიელია** → **აყენებს მიმდინარე თარიღს/დროს**
   - მუშაობს მხოლოდ თუ `effective_date_change` მოდული დაინსტალირებულია

### 3. **`stock.picking._auto_add_car_sawvav_product()`**
   - ამოწმებს არის თუ არა `picking_type.x_studio_car_sawvav` შევსებული
   - თუ პროდუქტი **არ არსებობს** move line-ებში → **ამატებს**
   - შექმნის ცარიელ move line-ს (quantity=0) მომხმარებლის შესავსებად
   - იძახება `create()` მეთოდიდან → მუშაობს **ყველგან** (UI, Barcode, API)

### 4. **`stock.move.line.picking_location_dest_id`**
   - აბრუნებს **warehouse view location**-ს (root)
   - ეს იძლევა საშუალებას XML domain `('id', 'child_of', picking_location_dest_id)` ყველა warehouse location-ს ნახოს

### 5. **`stock.location._search()`** ⭐ **KEY FIX**
   - **ამოწმებს** არის თუ არა `child_of` operator domain-ში
   - **შლის** `child_of` და `parent_of` შეზღუდვებს
   - ტოვებს მხოლოდ `usage` და `company_id` filters-ს

---

## დაინსტალირება (Installation)

### 1. დააკოპირეთ მოდული (Copy the module)

```bash
cp -r barcode_location_prompt /path/to/odoo/addons/
```

### 2. დააინსტალირეთ (Install)

**ვარიანტი A: Odoo UI-დან**
1. გადადით: **Apps** (აპლიკაციები)
2. დააჭირეთ **"Update Apps List"**
3. მოძებნეთ: `Barcode Location Prompt`
4. დააჭირეთ **"Install"**

**ვარიანტი B: Terminal-დან**
```bash
./odoo-bin -c /path/to/odoo.conf -d your_database -i barcode_location_prompt
```

---

## მოთხოვნები (Requirements)

- Odoo 18.0+
- `stock` module (core)
- `stock_barcode` module (Enterprise - საჭიროა Odoo Enterprise)

---

## გამოყენება (Usage)

### Barcode Interface-ში:

1. გადადით: **Inventory → Barcode**
2. აირჩიეთ **Internal Transfer** picking type
3. დაასკანეთ picking-ის barcode (მაგ. WH/INT/00201)
4. **ავტომატური ქცევა:**
   - `date_of_transfer` ველი **ავტომატურად შეივსება** მიმდინარე თარიღით/დროით
   - თუ picking type-ს აქვს `x_studio_car_sawvav` პროდუქტი
   - ეს პროდუქტი **ავტომატურად დაემატება** move line-ებში
   - რაოდენობა იქნება **ცარიელი (0)** - თქვენ შეავსებთ
5. დაასკანეთ სხვა პროდუქტების barcode-ები
6. **რაოდენობის შეცვლა:**
   - დააჭირეთ რაოდენობას (ციფრს) → გაიხსნება input ველი
   - შეიყვანეთ სასურველი რაოდენობა ხელით (მაგ. 5, 10, 15.5)
   - დააჭირეთ ✓ (შენახვა) ან Enter-ს
   - ან გამოიყენეთ +1 ღილაკი როგორც ადრე
6. **Destination Location** ველში:
   - ✅ გამოჩნდება **ყველა** internal/transit location
   - ✅ არა მხოლოდ picking type-ის default location-ის children

---

## თავსებადობა სხვა მოდულებთან (Compatibility)

### ✅ თავსებადია (Compatible):
- `default_location` - არ ერევა form view-ის ქცევაში
- `stock_location_product_filter` - მუშაობს ერთად
- ყველა სხვა stock-ის მოდული

### ⚠️ შენიშვნა (Note):
მოდული **ზოგადად ცვლის** `stock.location._search()` მეთოდს და **შლის** `child_of` შეზღუდვებს. ეს ზემოქმედებს **ყველა location search-ზე**, არა მხოლოდ barcode interface-ზე.

---

## ტექნიკური დეტალები (Technical Details)

### Override-ებული მეთოდები:

1. **`stock.picking._get_stock_barcode_data()`**
   - ცვლის barcode data-ს location lists-ს
   - აყენებს `date_of_transfer` ველს

2. **`stock.picking._set_date_of_transfer()`** 🆕
   - აყენებს მიმდინარე თარიღს/დროს

3. **`stock.move.line.picking_location_dest_id`** (computed field)
   - აბრუნებს warehouse view location-ს

4. **`stock.location._search()`** ⭐ **მთავარი ფიქსი**
   - შლის `child_of` და `parent_of` operators-ს domain-დან
   - უზრუნველყოფს სწორ domain syntax-ს

---

## ლიცენზია (License)

LGPL-3

---

## ავტორი (Author)

Custom Development

---

## ვერსია (Version)

**18.0.2.6.0** - Production Ready
- ✅ ყველა ლოკაციის არჩევა destination-ისთვის
- 🆕 ავტომატური პროდუქტის დამატება `x_studio_car_sawvav`-დან
- 🆕 ავტომატური `date_of_transfer` ველის შევსება მიმდინარე თარიღით
- 🆕 რაოდენობის შეტანის ველი - პირდაპირ ხელით შეყვანა

---

## Changelog

### v18.0.2.8.0 (2025-11-25) 🎉
- ✅ **სრულად მუშა ვერსია!** - რაოდენობა ინახება backend-ში
- ✅ Python method: `get_move_lines_by_picking_name()` - პოულობს move lines picking name-ით
- ✅ JavaScript: `getCurrentPickingName()` - იღებს "WH/INT/00162" HTML-დან
- ✅ Virtual ID mapping - აკავშირებს frontend virtual_id-ს backend move line-თან
- ✅ RPC call-ით ინახება `quantity`, `product_uom_qty`, `reserved_uom_qty`
- ✅ DOM-based injection qty-done-ის გვერდით
- ✅ European number format support (0,00 → 0.00)
- ✅ Duplicate prevention - მხოლოდ 1 input თითო line-ზე
- ✅ Success/Error notifications

### v18.0.2.7.0 (2025-11-25)
- 🎉 **მთლიანად მუშა ვერსია!** - რაოდენობა ინახება backend-ში
- ✅ RPC call-ით ინახება `stock.move.line.quantity` და `product_uom_qty`
- ✅ MutationObserver ავტომატურად პოულობს ახალ line-ებს
- ✅ DOM-based injection - XML template-ის გარეშე
- ✅ Success/Error notifications

### v18.0.2.6.1 (2025-11-24)
- 🔧 JavaScript-ის ფიქსი - უფრო საიმედო vanilla JS მიდგომა
- ✅ წინა ვერსიის component import პრობლემის გადაწყვეტა
- ✅ DOM-based ხელით რაოდენობის რედაქტირება

### v18.0.2.6.0 (2025-11-24)
- 🆕 დამატებულია რაოდენობის შეტანის ველი barcode ინტერფეისში
- ✅ შეგიძლიათ რაოდენობაზე დაწკაპუნებით input ველის გახსნა
- ✅ პირდაპირ რიცხვის შეყვანა ხელით (არა მხოლოდ +1)
- ✅ Enter-ით ან ✓ ღილაკით შენახვა
- ✅ CSS სტილები მოდერნული UI-სთვის

### v18.0.2.5.0 (2025-11-24)
- 🆕 დამატებულია ავტომატური `date_of_transfer` ველის შევსება მიმდინარე თარიღით/დროით
- ✅ მუშაობს barcode ინტერფეისში picking-ის გახსნისას
- ✅ თავსებადია `effective_date_change` მოდულთან

### v18.0.2.1.0 (2025-11-20)
- 🆕 დამატებულია ავტომატური პროდუქტის დამატება `picking_type.x_studio_car_sawvav` ველიდან
- ✅ პროდუქტი ემატება მხოლოდ ერთხელ (არა თუ უკვე არსებობს)
- ✅ რაოდენობა ცარიელია (0) - მომხმარებელი შეავსებს

### v18.0.2.0.0
- ✅ ყველა ლოკაციის არჩევის ფუნქციონალი
- ✅ Production ready release
