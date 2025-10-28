import os
import re

# List of user-facing template files to update
templates = [
    'animal_bite_first_aid.html',
    'after_care_reminder.html',
    'my_bookings.html',
    'book_appointment_type.html',
    'book_appointment_datetime.html',
    'appointment_summary.html',
    'appointment_details.html',
    'booking_details.html',
    'first_aid_donts.html',
    'edit_profile.html',
    'faq.html',
    'virtual_vaccine_card.html',
    'virtual_vaccine_card_back.html',
    'change_password.html'
]

base_path = r'c:\xampp2\htdocs\ABC-PWA Ichatbot\templates'
css_link = '    <link rel="stylesheet" href="/static/css/user_responsive.css">\n'

updated_count = 0
skipped_count = 0

for template in templates:
    file_path = os.path.join(base_path, template)
    
    if not os.path.exists(file_path):
        print(f"⚠️  Skipped (not found): {template}")
        skipped_count += 1
        continue
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if already has the responsive CSS
        if 'user_responsive.css' in content:
            print(f"✓  Already has responsive CSS: {template}")
            continue
        
        # Find the pattern after font-awesome or tailwindcss
        pattern = r'(.*<link rel="stylesheet" href="https://cdnjs\.cloudflare\.com/ajax/libs/font-awesome[^>]+>)\n'
        if re.search(pattern, content):
            new_content = re.sub(pattern, r'\1\n' + css_link, content, count=1)
        else:
            # Try after tailwindcss
            pattern = r'(.*<script src="https://cdn\.tailwindcss\.com"></script>)\n'
            if re.search(pattern, content):
                new_content = re.sub(pattern, r'\1\n' + css_link, content, count=1)
            else:
                # Try after any stylesheet link in head
                pattern = r'(<head>.*?)(</head>)'
                if re.search(pattern, content, re.DOTALL):
                    new_content = re.sub(pattern, r'\1' + css_link + r'\2', content, flags=re.DOTALL, count=1)
                else:
                    print(f"⚠️  Could not find insertion point: {template}")
                    skipped_count += 1
                    continue
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"✅ Updated: {template}")
        updated_count += 1
        
    except Exception as e:
        print(f"❌ Error updating {template}: {str(e)}")
        skipped_count += 1

print(f"\n✅ Successfully updated: {updated_count} files")
print(f"⚠️  Skipped: {skipped_count} files")
