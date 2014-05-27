""" This script takes the json extracted from the freebase jsons
 and creates a matrix of countries x FreeBase relations.
 We probably want to filter out relations and countries that do not 
 have a lot of values in the data"""
 
import json
from collections import Counter

with open("/cs/research/intelsys/home1/avlachos/FactChecking/allCountriesPost2010.json") as dataFile:
    data = json.loads(dataFile.read())
    
#print json.dumps(data, sort_keys=True, indent=4)
print len(data)
filteredFeatureCounts = Counter()
filteredCountries = {}
for country, numbers in data.items():
    if len(numbers) >= 2:
        filteredCountries[country] = numbers
        for feature in numbers:
            filteredFeatureCounts[feature] += 1
        

print filteredFeatureCounts 

filteredFeatureCountries = {}
for country, numbers in filteredCountries.items():
    filteredFeatures = {}
    for feature, number in numbers.items():
        if filteredFeatureCounts[feature] >= 10:
            filteredFeatures[feature] = number
    filteredFeatureCountries[country] = filteredFeatures

print len(filteredFeatureCountries)

with open("/cs/research/intelsys/home1/avlachos/FactChecking/allCountriesPost2010Filtered.json", "w") as dataFile:
    json.dump(filteredFeatureCountries, dataFile)


#print len(featureCounts)
#print data["Algeria"]
#print data["Germany"]["/location/statistical_region/population"]
#print data["Algeria"]["/location/statistical_region/population"]

#print featureCounts.most_common(40)
 