import argparse
import csv
import random
import os
from datetime import datetime, timedelta

def main():
  parser = argparse.ArgumentParser(description="Deterministic Mock BBPS Biller Dataset Generator")
  parser.add_argument("--count", type=int, default=10000, help="Number of biller records to generate")
  parser.add_argument("--seed", type=int, default=42, help="Seed value for deterministic random generation")
  parser.add_argument("--output", type=str, default="mock_billers_10000.csv", help="Output filename")
  args = parser.parse_args()

  # Set seed for reproducibility
  random.seed(args.seed)

  categories = [
    "Electricity", "Water", "Gas", "Telecom", "Broadband", "DTH", 
    "Insurance", "FASTag", "Municipal Tax", "Housing Society", 
    "Education", "Credit Card", "Loan EMI", "Subscription Services"
  ]

  regions = ["National", "North", "South", "East", "West", "Central", "NorthEast"]

  states_by_region = {
    "National": ["National"],
    "North": ["Uttar Pradesh", "Delhi", "Punjab", "Haryana", "Rajasthan", "Himachal Pradesh", "Jammu and Kashmir"],
    "South": ["Karnataka", "Tamil Nadu", "Telangana", "Kerala", "Andhra Pradesh"],
    "East": ["West Bengal", "Bihar", "Odisha", "Jharkhand"],
    "West": ["Maharashtra", "Gujarat", "Goa"],
    "Central": ["Madhya Pradesh", "Chhattisgarh"],
    "NorthEast": ["Assam", "Sikkim", "Meghalaya", "Manipur", "Mizoram", "Tripura", "Arunachal Pradesh", "Nagaland"]
  }

  cities_by_state = {
    "National": ["National"],
    "Uttar Pradesh": ["Lucknow", "Noida", "Kanpur", "Varanasi", "Agra", "Ghaziabad"],
    "Delhi": ["New Delhi", "Dwarka", "Rohini", "Saket"],
    "Punjab": ["Chandigarh", "Ludhiana", "Amritsar", "Jalandhar"],
    "Haryana": ["Gurgaon", "Faridabad", "Panipat", "Ambala"],
    "Rajasthan": ["Jaipur", "Jodhpur", "Udaipur", "Kota"],
    "Karnataka": ["Bangalore", "Mysore", "Hubli", "Mangalore"],
    "Tamil Nadu": ["Chennai", "Coimbatore", "Madurai", "Trichy"],
    "Telangana": ["Hyderabad", "Warangal", "Nizamabad"],
    "Kerala": ["Kochi", "Trivandrum", "Calicut", "Thrissur"],
    "Andhra Pradesh": ["Vijayawada", "Visakhapatnam", "Tirupati"],
    "West Bengal": ["Kolkata", "Howrah", "Durgapur", "Siliguri"],
    "Bihar": ["Patna", "Gaya", "Muzaffarpur"],
    "Odisha": ["Bhubaneswar", "Cuttack", "Rourkela"],
    "Maharashtra": ["Mumbai", "Pune", "Nagpur", "Thane", "Nashik"],
    "Gujarat": ["Ahmedabad", "Surat", "Vadodara", "Rajkot"],
    "Madhya Pradesh": ["Bhopal", "Indore", "Gwalior", "Jabalpur"]
  }

  # Fallback lists if states/cities are not in dictionaries
  all_states = ["Uttar Pradesh", "Maharashtra", "Karnataka", "Tamil Nadu", "Delhi", "West Bengal", "Gujarat", "Telangana"]
  all_cities = ["Mumbai", "Delhi", "Bangalore", "Chennai", "Kolkata", "Hyderabad", "Pune", "Ahmedabad", "Lucknow", "Jaipur"]

  payment_methods = ["CreditCard", "DebitCard", "NetBanking", "UPI"]

  headers = [
    "biller_id", "biller_name", "category", "region", "state", "city", 
    "support_email", "support_phone", "payment_modes", "minimum_amount", 
    "maximum_amount", "active_status", "provider_latency_ms", "failure_probability", 
    "created_at"
  ]

  # Ensure output directory exists if filename includes paths
  out_dir = os.path.dirname(args.output)
  if out_dir:
    os.makedirs(out_dir, exist_ok=True)

  print(f"Generating {args.count} mock biller records with seed {args.seed}...")

  start_date = datetime.now() - timedelta(days=365)

  with open(args.output, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(headers)

    for i in range(1, args.count + 1):
      category = random.choice(categories)
      region = random.choice(regions)
      
      # Select state and city matching region
      states_list = states_by_region.get(region, all_states)
      state = random.choice(states_list)
      
      cities_list = cities_by_state.get(state, all_cities)
      city = random.choice(cities_list)

      # Generate unique biller ID
      # ID format: MOCK + Category short (3 char) + 5 digits index + Region/State short (3 char)
      cat_prefix = category[:3].upper()
      reg_suffix = (state[:3] if state != "National" else region[:3]).upper()
      biller_id = f"MOCK{cat_prefix}{i:05d}{reg_suffix}"

      # Generate operator name
      biller_name = f"{state} {category} Board {i}"
      if state == "National":
        biller_name = f"National {category} Services {i}"

      # Generate support email & phone
      clean_name = biller_name.lower().replace(" ", "")
      support_email = f"support_{i}@{clean_name[:12]}.in"
      support_phone = f"91{random.randint(7000000000, 9999999999)}"

      # Select payment modes
      modes_count = random.randint(2, 4)
      modes = random.sample(payment_methods, modes_count)
      payment_modes_str = ";".join(modes)

      # Latencies and drop probabilities by category for realism
      if category in ["Electricity", "Telecom", "FASTag"]:
        min_lat, max_lat = 50, 200
        fail_prob = round(random.uniform(0.005, 0.03), 4) # 0.5% - 3%
      elif category in ["Municipal Tax", "Education", "Insurance"]:
        min_lat, max_lat = 300, 1200
        fail_prob = round(random.uniform(0.04, 0.12), 4) # 4% - 12%
      else:
        min_lat, max_lat = 100, 500
        fail_prob = round(random.uniform(0.02, 0.07), 4) # 2% - 7%

      latency = random.randint(min_lat, max_lat)

      min_amt = f"{random.choice([5.00, 10.00, 50.00, 100.00]):.2f}"
      max_amt = f"{random.choice([10000.00, 50000.00, 100000.00, 500000.00]):.2f}"

      active_status = "ACTIVE" if random.random() < 0.96 else "INACTIVE"
      
      created_time = start_date + timedelta(seconds=random.randint(0, 365 * 24 * 3600))
      created_at_str = created_time.strftime("%Y-%m-%dT%H:%M:%S+05:30")

      row = [
        biller_id, biller_name, category, region, state, city,
        support_email, support_phone, payment_modes_str, min_amt,
        max_amt, active_status, latency, fail_prob, created_at_str
      ]
      writer.writerow(row)

  print(f"Successfully generated dataset: {args.output}")

if __name__ == "__main__":
  main()
