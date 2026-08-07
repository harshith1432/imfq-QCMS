import fitz
import os
import sys

# Insert paths to import models if needed, but for now we'll mock the data
# just to get the layout right.

labels_mapping = {
    'Project Title': "Increase Yield on Line A",
    'Case / Report No.': "PROJ-1234",
    'Plant / Line': "Plant 1 / Line A",
    'Part / Process': "Assembly",
    'Date of Closure': "2026-07-25",
    'Prepared By (Team Leader)': "John Doe",
    'QC Theme / Defect Type': "Scratches",
    'Target Area / Line / Part No.': "Housing Part X",
    'Symptom (What / Where Observed)': "Scratches on front panel during final check",
    'Scale (How Much': "1500 PPM",
    'Keywords / Search Tags': "scratches, housing, assembly",
    'Root Cause (5 -Why, Level 5)': "Dust accumulated on fixture pads",
    'Failure Mode (Man / Machine / Material / Method)': "Machine",
    'Validation Method Used': "Trial without cleaning vs cleaning",
    'Interim Containment (Use Today)': "Clean pads every shift",
    'Permanent Corrective Action': "Installed auto-cleaning brush",
    'Redeployment Effort (Ease / Cost / Impact)': "Low / $500 / High",
    'Linked SOP / Standard Doc No.': "SOP-999-Clean",
    'Baseline Metric': "1500 PPM -> 200 PPM",
    '% Improvement': "86%",
    'Net Benefit Realized': "50,000 INR/yr",
    'Still Holding?': "Yes (2026-07-20 / Pass)"
}

doc = fitz.open(r'd:\projects softwares\imfq\backend\app\utils\QC_Story_Closure_Summary_Template.pdf')

for page in doc:
    for label, value in labels_mapping.items():
        rects = page.search_for(label)
        if rects:
            rect = rects[0]
            # determine x position based on the label's right edge
            # For the top section, it's a 2 column table, so we need to be careful
            if rect.y1 < 150:
                if rect.x0 < 100: # left column
                    x = 135
                else: # right column
                    x = 415
            else:
                x = 220
                if label == 'Baseline Metric':
                    x = 220
                if 'Improvement' in label:
                    x = 130
                    
            y = rect.y1
            page.insert_text((x, y), value, fontsize=9, color=(0, 0, 1)) # blue text for filled data

doc.save('test_output.pdf')
print("Saved test_output.pdf")
