
# coding: utf-8

# In[ ]:

import arcpy 

arcpy.env.addOutputsTomap = True 

InputFile = arcpy.GetParameterAsText(0) # The input feature class
Field = arcpy.GetParameterAsText(1) # The filed that needs to be reclassified
Outfield = arcpy.GetParameterAsText(2) # Name the new field

new_row = arcpy.AddField_management(InputFile, Outfield, "double")
# Create a new field everytime run this tool and user can define it.


cursor = arcpy.da.UpdateCursor(InputFile, [Field, Outfield] ) 
#Update the new field based on the following classification.

for row in cursor: 
    if 0 <= row[0] <= 100: 
        row[1] = 1	 
    elif 100 < row[0] <= 800: 
        row[1] = 2 
    elif 1200 <= row[0] <= 4000: 
        row[1] = 3 
    elif 4000 < row[0] <= 100000: 
        row[1] = 4 
    else: 
        row[1] = 666 
    
    cursor.updateRow(row)

Output = arcpy.GetParameterAsText(3) # Set up output.

arcpy.CopyFeatures_management(InputFile, Output)

# At first, I was really confused about the whole parameter thing but after
# couple tries and I found out it's much more understandable than I thought.

