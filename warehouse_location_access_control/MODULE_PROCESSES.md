# Warehouse Location Access Control - Module Processes

## მოდულის მიზანი
ეს მოდული აზღუდავს მომხმარებლების წვდომას ლოკაციებზე Internal Transfers-ში Odoo-ში.

## რა პროცესებს ასრულებს მოდული

### 1. **მომხმარებლის ლოკაციების მენეჯმენტი** (`models/res_users.py`)
- **პროცესი**: მომხმარებლებს შეუძლიათ მიუთითონ "Allowed Locations" ველში, რომელ ლოკაციებზე აქვთ წვდომა
- **სად**: Settings > Users & Companies > Users > "Allowed Locations" ტაბი
- **როგორ მუშაობს**: 
  - მომხმარებელი ირჩევს ლოკაციებს, რომლებზეც აქვს წვდომა
  - თუ ლოკაციები არ არის მითითებული, მომხმარებელს ექნება წვდომა ყველა ლოკაციაზე (backward compatibility)

### 2. **Internal Transfer-ების Domain შეზღუდვა** (`models/stock_picking.py`)

#### 2.1. **Form-ის ჩატვირთვისას** (`fields_get` მეთოდი)
- **პროცესი**: როცა Internal Transfer-ის form იტვირთება, domain ავტომატურად იყენებს მხოლოდ allowed locations-ს
- **როცა**: Form-ის ჩატვირთვისას ან როცა record იხსნება
- **როგორ**: `fields_get` მეთოდი ამოწმებს, არის თუ არა Internal Transfer და აყენებს domain-ს `location_id` და `location_dest_id` ველებზე

#### 2.2. **Picking Type-ის შეცვლისას** (`_onchange_picking_type_location_domain` მეთოდი)
- **პროცესი**: როცა `picking_type_id` იცვლება, onchange მეთოდი ამოწმებს, არის თუ არა Internal Transfer
- **როცა**: `picking_type_id` ველის შეცვლისას
- **როგორ**: 
  - თუ Internal Transfer არის, domain იყენებს მხოლოდ allowed locations-ს
  - თუ მხოლოდ ერთი allowed location არის, ის ავტომატურად აირჩევა `location_id`-სთვის

#### 2.3. **Default Location-ის დაყენება** (`default_get` მეთოდი)
- **პროცესი**: როცა ახალი Internal Transfer იქმნება, თუ მომხმარებელს მხოლოდ ერთი allowed location აქვს, ის დეფოლტად აირჩევა
- **როცა**: ახალი Internal Transfer-ის შექმნისას
- **როგორ**: `default_get` მეთოდი ამოწმებს allowed locations-ს და თუ მხოლოდ ერთია, ის დეფოლტად აირჩევა

### 3. **View Modifications** (`views/stock_picking_view.xml`)
- **პროცესი**: ამატებს options-ს location fields-ზე
- **როცა**: Form-ის ჩატვირთვისას
- **როგორ**: 
  - ამატებს `no_create` და `no_create_edit` options-ს `location_id` და `location_dest_id` ველებზე
  - Domain დაყენებულია `fields_get` და onchange მეთოდების გამოყენებით

## Domain-ის მუშაობის პრინციპი

1. **Form-ის ჩატვირთვისას**: `fields_get` მეთოდი აყენებს domain-ს `location_id` და `location_dest_id` ველებზე
2. **Picking Type-ის შეცვლისას**: `_onchange_picking_type_location_domain` მეთოდი აყენებს domain-ს onchange-ის გამოყენებით
3. **Domain-ის შინაარსი**: `[('id', 'in', allowed_ids)]` - მხოლოდ allowed location IDs-ს აჩვენებს

## შეზღუდვები

- **მხოლოდ Internal Transfers**: Domain შეზღუდვა მუშაობს მხოლოდ Internal Transfers-ში
- **სხვა Picking Types**: სხვა picking types-ისთვის (Receipts, Delivery, etc.) domain არ არის შეზღუდული
- **Backward Compatibility**: თუ მომხმარებელს არ აქვს allowed locations, მას ექნება წვდომა ყველა ლოკაციაზე

## პრობლემები და გადაწყვეტილებები

### პრობლემა: Domain არ განახლდება, როცა location_id ირჩევა
**გადაწყვეტილება**: Domain დაყენებულია `fields_get` მეთოდში form-ის ჩატვირთვისას და `_onchange_picking_type_location_domain` მეთოდში picking type-ის შეცვლისას. Domain view-ში არ არის დაყენებული, რადგან Odoo არ განახლებს computed field-ის ცვლილებას.

