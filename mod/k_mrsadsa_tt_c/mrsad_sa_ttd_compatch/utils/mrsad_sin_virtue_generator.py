import codecs
import regex
import os.path
#Text files to get Sin / Virtues from
trait_sources=["E:\\SteamLibrary\\SteamApps\\common\\Crusader Kings III\\game\\common\\traits\\00_traits.txt"]
tenets_source = "mz_core_tenets_1.9.2_5.30.2023.txt"

doctrine_output_folder="..\\common\\religion\\doctrines"
events_output_folder="..\\events\\religion_events\\"
localization_output_folder = "..\\localization"
scripted_effects_output_folder="..\\common\\scripted_effects"

doctrine_output_pre = "zz_"
doctrine_output_mid = "s"
doctrine_output_end = ".txt"
tenets_output = "zz_tt_mrsad_core_tenets.txt"
creation_event_output = "faith_creation_mrsad_events.txt"
startup_effects_output = "mrsad_startup_effects.txt"
localization_output_pre = "mrsad_l_"
localization_output_end = ".yml"
no_of_slots = 12
no_of_empty_tenet_slots = 22
default_picks = 3
doctrine_types = ["sin","virtue"]
#First entry is single trait strength, second is group (so single takes priority at same tier)
#Scale is a float (by the documentation), Weight is an integer (by a disturbingly large amount of time spent troubleshooting >_>)
virtue_sin_strength = [[["","","",""],[3,2],1],[["strong","_strong"," great", " (Great)"],[5,4],2]]

#These traits will be used as Sins / Virtues even if they would normally be blocked
#trait_whitelist = []  #Not doing any checking yet, so no whitelist
#trait_group_whitelist = []  #Not doing any checking yet, so no whitelist

#These traits will not be used as Sins / Virtues even if they would normally be allowed
trait_blacklist_hidden = ["early_great_pox"] #Early Great Pox looks like lover's pox and should be treated identically. Special code adds both when Lover's Pox is selected
trait_blacklist_crime_standard = ["adulterer","fornicator","incestuous","kinslayer_1","kinslayer_2","kinslayer_3","murderer","sodomite"] #Crime doctrines are implicitly sins (in vanilla) or virtues (if celebrated) and these ones do not appear if accepted.
trait_blacklist_indistinguishable = ["depressed_1","depressed_genetic","lunatic_1","lunatic_genetic","possessed_1","possessed_genetic"] #All current Group Equivalents are genetic and non-genetic variants of the same mental trait, since there's no way to tell these apart in world block taking them individually.
trait_blacklist_crime_special = ["cannibal","excommunicated"] #Cannibal is blacklisted gemerally (despite being a special crime doctrine that appears even if accepted ) becasue the Tenet that permits it also makes it a strong virtue already. #Makes no sense for excommunicated to be a sin on top of it's intrinsic nature and doesn't really work as a Virtue since it's not possible to have in faiths that might think it virtuous (ie ones without Communion).
trait_blacklist_unique = ["saoshyant","savior","chakravarti","greatest_of_khans"] #These are traits that only one person can have and so don't make sense as virtues/sins (they should be folded in with equivalent more general traits if relevant though (eg Descendant traits))
trait_blacklist_religious = ["hajjaj","pilgrim","devoted","sayyid","saoshyant_descendant","divine_blood","blood_of_prophet","faith_warrior","saint","order_member","heresiarch","crusader_king","paragon","consecrated_blood"]  #These already have strong religious implications in ways that make them unfitting to be sins or virtues
trait_blacklist = []
trait_blacklist.extend(trait_blacklist_hidden)
trait_blacklist.extend(trait_blacklist_crime_standard)
trait_blacklist.extend(trait_blacklist_indistinguishable)
trait_blacklist.extend(trait_blacklist_crime_special)
trait_blacklist.extend(trait_blacklist_unique)
trait_blacklist.extend(trait_blacklist_religious)


trait_group_blacklist = ["kinslayer"]
trait_group_equivalent_blacklist = []
trait_virtue_blacklist = ["bastard","denounced","disinherited","witch","deviant"] #Bastard doesn't make sense as a virtue because it only appears if you have a negative doctrine. #Dynasty condemnation doesn't make sense as a virtue because it works based on scorn. #Witch is already handled by the game as a virtue. #As is Deviant (though it's perhaps too restricted)
trait_group_virtue_blacklist = []
trait_group_equivalent_virtue_blacklist = []
trait_sin_blacklist = ["deviant","witch","reincarnation","child_of_concubine_female","child_of_concubine_male"]  #Deviant, Witch & Cannibal are special crime doctrines that can appear even if accepted. So blacklist as sins (should be handled by Crime Doctrine) but allow as Virtues. #Reincaranted should not be a sin because it can only appears in faiths that should approve. #Child of Concubine should not be a sin because it only appears if Concubines are accepted.
trait_group_sin_blacklist = ["child_of_concubine"] #Child of Concubine should not be a sin because only appears if Concubines are accepted
trait_group_equivalent_sin_blacklist = []

trait_regex=r"(?P<trait_name>[a-z][a-z_1-9]*+) ?= ?(?P<trait_description>\{[^}{]*+(?:(?P>trait_description)[^}{]*)*+\})"
standard_values_regex=r"(?P<sv_name>@[a-z][a-z_1-9]*+) ? = ?(?P<sv_value>-?[0-9]+)" 
trait_parameter_regex = r"(?P<trait_parameter_name>[a-z][a-z_1-9]*+) ?= ?((?P<trait_parameter_desc_c>\{[^}{]*+(?:(?P>trait_parameter_desc_c)[^}{]*)*+\})|(?P<trait_parameter_desc_s>.*+\n))"
slot_picks_regex=r"(?P<sp_name>number_of_picks) ? = ?(?P<sp_value>[0-9]+)" 


def opposite_doctrine_type(doctrine_type):
    doctrine_index = doctrine_types.index(doctrine_type)
    return doctrine_types[doctrine_index - 1]

def isInTraitGroup(trait):
    trait_group_parameter = filter(lambda parameter: parameter['name'] == "trait_group", trait.parameters)
    return trait_group_parameter.len() > 0

def main():
    traits = {}
    trait_groups = {}
    trait_group_equivalents = {}
    standard_values = {}

    for source in trait_sources:
        with codecs.open(source,"r",'utf-8-sig') as f:
            e = f.read()

        sv_raw = regex.findall(standard_values_regex,e)
        for standard_value in sv_raw:
            standard_values[standard_value[0]] = int(standard_value[1],10)

        traits_raw = regex.findall(trait_regex,e)
        for trait in traits_raw:
            traits[trait[0]] = {'_raw':trait[1],'parameters':[]}
            parameters_raw = regex.findall(trait_parameter_regex,trait[1])
            for parameter in parameters_raw:
                this_parameter={'name':parameter[0],'_raw':parameter[1],'_complex':parameter[1] == parameter[2]}
                if not this_parameter['_complex']:
                    #Simple parameter so lets try and process it
                    value = parameter[1].strip()
                    try: #Integer
                        value = int(value,10)
                    except:
                        try:
                            value = float(value)
                        except:
                            if (value == "yes"):
                                value = True;
                            elif (value == "no"):
                                value = False;
                            #else #Implicitly a string
                    this_parameter['value'] = value
                    if parameter[0] == 'group': #Levelled Traits
                        try:
                            trait_groups[value]["traits"].append(trait[0])
                        except:
                            trait_groups[value] = {"traits":[trait[0]]}
                    if parameter[0] == 'group_equivalence': #Traits with a Non-Genetic and Genetic Equivalent
                        try:
                            trait_group_equivalents[value]["traits"].append(trait[0])
                        except:
                            trait_group_equivalents[value] = {"traits":[trait[0]]}
                else: #Could process complex trait parameters here if need be
                    #Basic parse of complex parameter to check if it's just a set of simples or a conditional.
                    sub_parameters_raw = regex.findall(trait_parameter_regex,parameter[2])
                    this_parameter['value'] = {'_raw':sub_parameters_raw,'sub_parameters':[]}
                    for sub_parameter in sub_parameters_raw:
                        this_sub_parameter = {'name':sub_parameter[0],'_raw':sub_parameter[1],'_complex':sub_parameter[1] == sub_parameter[2]}
                        if not this_sub_parameter['_complex']:
                            value = sub_parameter[1].strip()
                            try: #Integer
                                value = int(value,10)
                            except:
                                try:
                                    value = float(value)
                                except:
                                    if (value == "yes"):
                                        value = True;
                                    elif (value == "no"):
                                        value = False;
                                    #else #Implicitly a string
                            this_sub_parameter['value'] = value
                        else:
                            #Sub parameter contains complexity
                            #Just stash the raw data
                            this_sub_parameter['value'] = sub_parameter[1]
                        this_parameter['value']['sub_parameters'].append(this_sub_parameter)
                traits[trait[0]]['parameters'].append(this_parameter)

        #Setup Groups with Levels
        for trait_group in trait_groups:            
            trait_groups[trait_group]["levels"] = {}
            for trait in trait_groups[trait_group]["traits"]:
                for parameter in traits[trait]["parameters"]:
                    if parameter["name"] == "level":
                        trait_groups[trait_group]["levels"][parameter["value"]] = trait 
        for trait_group_equivalent in trait_group_equivalents:
            trait_group_equivalents[trait_group_equivalent]["levels"] = {}
            for trait in trait_group_equivalents[trait_group_equivalent]["traits"]:
                for parameter in traits[trait]["parameters"]:
                    if parameter["name"] == "level":
                        trait_group_equivalents[trait_group_equivalent]["levels"][parameter["value"]] = trait 


        #Debug stuff
        #print('Standard Values')        
        #for standard_value in standard_values:
        #    print(standard_value)
        #    print(standard_values[standard_value])
        #    input("Continue")

        #print('Trait Groups')        
        #for trait_group in trait_groups:
        #    print(trait_group)
        #    print(trait_groups[trait_group]["levels"])
        #    input("Continue")
        #print("Trait Group Equivalents")
        #for trait_group_equivalent in trait_group_equivalents:
        #    print(trait_group_equivalent)
        #    print(trait_group_equivalents[trait_group_equivalent]["levels"])
        #    input("Continue")
        #print("Traits")
        #for trait in traits:
        #    print(trait)
        #    print(traits[trait])
        #    input("Continue")
    
    #Generate output
    
    
    #Sins
    for doctrine_type in doctrine_types:
            with codecs.open(os.path.join(doctrine_output_folder,doctrine_output_pre+doctrine_type+doctrine_output_mid+doctrine_output_end),"w",'utf-8-sig') as f:
                #for i in range(1,no_of_slots+1):

                    #f.write(str(codecs.BOM_UTF8)) #BOM
                    
                    #Doctrine
                    f.write("doctrine_mrsad_" + doctrine_type + "s = {" + "\n")
                    #Group
                    f.write('\t'+'group = "mrsad_'+doctrine_type+'s"' + "\n")
                    f.write('\t'+'number_of_picks = ' + str(no_of_slots) + "\n")
                    f.write("" + "\n")

                    #Trait Group Equivalent Traits are banned from appearing individually (because there's no reasonable way for someone to tell them apart in game)
                    #group_equivalent_only = []
                    #for trait_group_equivalent in trait_group_equivalents:
                    #    group_equivalent_only.extend(trait_group_equivalents[trait_group_equivalent]["levels"].values())

                    for trait in traits:
                        if (not (trait in trait_blacklist)) and (doctrine_type == "virtue" or not (trait in trait_sin_blacklist)) and (doctrine_type == "sin" or (not trait in trait_virtue_blacklist)):
                            #if not (trait in group_equivalent_only):
                            for strength in virtue_sin_strength:
                                #Doctrines
                                doctrine_name = "doctrine_" + doctrine_type+ "_" + trait + strength[0][1]
                                doctrine_opposite_name = "doctrine_" + opposite_doctrine_type(doctrine_type)+ "_" + trait + strength[0][1]
                                f.write( "\t" + doctrine_name + " = {" + "\n")
                                f.write( "\t" + "\t" + "name = {" + "\n")
                                f.write( "\t" + "\t" + "\t" + "first_valid = {" + "\n")
                                f.write( "\t"+ "\t" + "\t" + "\t" + "desc = " + doctrine_name + "_ingame_name" + "\n")
                                f.write( "\t" + "\t" + "\t" + "}" + "\n")
                                f.write( "\t" + "\t" + "}" + "\n")
                                f.write( "\t" + "\t" + "desc = {" + "\n")
                                f.write( "\t" + "\t" + "\t" + "first_valid = {" + "\n")
                                f.write( "\t"+ "\t" + "\t" + "\t" + "desc = " + doctrine_name + "_ingame_desc" + "\n")
                                f.write( "\t" + "\t" + "\t" + "}" + "\n")
                                f.write( "\t" + "\t" + "}" + "\n")
                                f.write( "\t" + "\t" + "piety_cost = {" + "\n")
                                f.write( "\t" + "\t" + "\t" + "value = faith_doctrine_cost_low" + "\n")
                                cost = 0
                                for parameter in traits[trait]["parameters"]:
                                    if parameter["name"] == "ruler_designer_cost":
                                        cost += parameter["value"]
                                if doctrine_type == "sin":
                                    f.write( "\t" + "\t" + "\t" + "subtract = " + str(cost) + "\n") #Cheaper to make beneficial things sins
                                else:    
                                    f.write( "\t" + "\t" + "\t" + "add = " + str(cost) + "\n")
                                f.write( "\t" + "\t" + "\t" + "if = {" + "\n")
                                f.write( "\t"+ "\t" + "\t" + "\t" + "limit = { has_doctrine =  " + doctrine_name + " }" + "\n")
                                f.write( "\t"+ "\t" + "\t" + "\t" + "multiply = faith_unchanged_doctrine_cost_mult" + "\n")
                                f.write( "\t" + "\t" + "\t" + "}" + "\n")
                                f.write( "\t" + "\t" + "}" + "\n")
                                f.write( "\t" + "\t" + "is_shown = {" + "\n")
                                f.write( "\t"+ "\t" + "\t" + "always = yes" + "\n")
                                if (doctrine_type == "sin" or not (trait in trait_sin_blacklist)) and (doctrine_type == "virtue" or (not trait in trait_virtue_blacklist)):
                                    f.write( "\t"+ "\t" + "\t" + "NOT = { doctrine:" + doctrine_opposite_name + " = { is_in_list = selected_doctrines } }" + "\n")
                                f.write( "\t" + "\t" + "}" + "\n")
                                f.write( "\t" + "\t" + "can_pick = {" + "\n")
                                f.write( "\t" + "\t" +  "\t" + "always = yes" + "\n") #Default evaluation is and so this is effectively blank 
                                groupStrongQualifier = False
                                level = None
                                lifestyle = False
                                genetic = False
                                education = False
                                for trait_group in trait_groups:
                                    if trait in trait_groups[trait_group]["levels"].values():
                                        for parameter in traits[trait]["parameters"]:
                                            if parameter["name"] == "level":
                                                level = parameter["value"] 
                                            if parameter["name"] == "lifestyle":
                                                lifestyle = parameter["value"]
                                            if parameter["name"] == "genetic":
                                                genetic = parameter["value"]
                                            if parameter["name"] == "education":
                                                education = parameter["value"]
                                        if not lifestyle: #Lifestyle traits can level up, so they can convey things about attitudes to learning / hubris / etc so no restrictions (also in vanilla these are all 3 levels so can't have silly things like 2/4 or 1/3) 
                                            f.write( "\t" + "\t" + "\t" +"custom_description = {" + "\n")
                                            f.write( "\t" + "\t" + "\t" + "\t" +"text = doctrine_requires_sequential_traits_"+doctrine_type+"_trigger" +"\n" )
                                            if max(trait_groups[trait_group]["levels"].keys()) == 3: #3 Levels, fixed
                                                if level == 1:
                                                    f.write( "\t" + "\t" + "\t" + "\t" + "OR = {" + "\n")
                                                    f.write( "\t" + "\t" + "\t" + "\t" + "\t" + "NOT = { doctrine:doctrine_" + doctrine_type+ "_" + trait_groups[trait_group]["levels"][3] + strength[0][1] + " = { is_in_list = selected_doctrines } }" + "\n")
                                                    f.write( "\t" + "\t" + "\t" + "\t" + "\t" + "doctrine:doctrine_" + doctrine_type+ "_" + trait_groups[trait_group]["levels"][2] + strength[0][1] + " = { is_in_list = selected_doctrines }" + "\n")
                                                    f.write( "\t" + "\t" + "\t" + "\t" + "}" + "\n")
                                                if level == 2:
                                                    f.write( "\t" + "\t" + "\t" + "\t" + "OR = {" + "\n")
                                                    f.write( "\t" + "\t" + "\t" + "\t" + "\t" + "doctrine:doctrine_" + doctrine_type+ "_" + trait_groups[trait_group]["levels"][3] + strength[0][1] + " = { is_in_list = selected_doctrines }" + "\n")
                                                    f.write( "\t" + "\t" + "\t" + "\t" + "\t" + "doctrine:doctrine_" + doctrine_type+ "_" + trait_groups[trait_group]["levels"][1] + strength[0][1] + " = { is_in_list = selected_doctrines }"+ "\n")
                                                    f.write( "\t" + "\t" +  "\t" + "}" + "\t" + "\n")
                                                if level == 3:
                                                    f.write( "\t" + "\t" + "\t" + "\t" + "OR = {" + "\n")
                                                    f.write( "\t" + "\t" + "\t" + "\t" + "\t" + "NOT = { doctrine:doctrine_" + doctrine_type+ "_" + trait_groups[trait_group]["levels"][1] + " = { is_in_list = selected_doctrines } }" + "\n")
                                                    f.write( "\t" + "\t" + "\t" + "\t" + "\t" + "doctrine:doctrine_" + doctrine_type+ "_" + trait_groups[trait_group]["levels"][2] + strength[0][1] + " = { is_in_list = selected_doctrines }" + "\n")
                                                    f.write( "\t" + "\t" + "\t" + "\t" + "}" + "\n")
                                            elif max(trait_groups[trait_group]["levels"].keys()) == 4: #4 Levels, fixed
                                                if level == 1:
                                                    f.write( "\t" + "\t" + "\t" + "\t" + "OR = {" + "\n")
                                                    f.write( "\t" + "\t" + "\t" + "\t" + "\t" + "NOR = {" +  "\n")
                                                    f.write( "\t" + "\t" + "\t" + "\t" + "\t" + "\t" + "doctrine:doctrine_" + doctrine_type + "_" + trait_groups[trait_group]["levels"][3] + strength[0][1] + " = { is_in_list = selected_doctrines }" + "\n")
                                                    f.write( "\t" + "\t" + "\t" + "\t" + "\t" + "\t" + "doctrine:doctrine_" + doctrine_type + "_" + trait_groups[trait_group]["levels"][4] + strength[0][1] + " = { is_in_list = selected_doctrines }" + "\n")
                                                    f.write( "\t" + "\t" + "\t" + "\t" + "\t" + "}" +  "\n")
                                                    f.write( "\t" + "\t" + "\t" + "\t" + "\t" + "doctrine:doctrine_" + doctrine_type+ "_" + trait_groups[trait_group]["levels"][2] + strength[0][1] + " = { is_in_list = selected_doctrines }" + "\n")
                                                    f.write( "\t" + "\t" + "\t" + "\t" + "}" + "\n")
                                                if level == 2:
                                                    f.write( "\t" + "\t" + "\t" + "\t" + "OR = {" + "\n")
                                                    f.write( "\t" + "\t" + "\t" + "\t" + "\t" + "doctrine:doctrine_" + doctrine_type+ "_" + trait_groups[trait_group]["levels"][1] + strength[0][1] + " = { is_in_list = selected_doctrines }" + "\n")
                                                    f.write( "\t" + "\t" + "\t" + "\t" + "\t" + "doctrine:doctrine_" + doctrine_type+ "_" + trait_groups[trait_group]["levels"][3] + strength[0][1] + " = { is_in_list = selected_doctrines }" + "\n")
                                                    f.write( "\t" + "\t" + "\t" + "\t" + "}" + "\n")
                                                if level == 3:
                                                    f.write( "\t" + "\t" + "\t" + "\t" + "OR = {" + "\n")
                                                    f.write( "\t" + "\t" + "\t" + "\t" + "\t" + "doctrine:doctrine_" + doctrine_type+ "_" + trait_groups[trait_group]["levels"][2] + strength[0][1] + " = { is_in_list = selected_doctrines }" + "\n")
                                                    f.write( "\t" + "\t" + "\t" + "\t" + "\t" + "doctrine:doctrine_" + doctrine_type+ "_" + trait_groups[trait_group]["levels"][4] + strength[0][1] + " = { is_in_list = selected_doctrines }" + "\n")
                                                    f.write( "\t" + "\t" + "\t" + "\t" + "}" + "\n")
                                                if level == 4:
                                                    f.write( "\t" + "\t" + "\t" + "\t" + "OR = {" + "\n")
                                                    f.write( "\t" + "\t" + "\t" + "\t" + "\t" + "NOR = {" +  "\n")
                                                    f.write( "\t" + "\t" + "\t" + "\t" + "\t" + "\t" + "doctrine:doctrine_" + doctrine_type + "_" + trait_groups[trait_group]["levels"][1] + strength[0][1] + " = { is_in_list = selected_doctrines }" + "\n")
                                                    f.write( "\t" + "\t" + "\t" + "\t" + "\t" + "\t" + "doctrine:doctrine_" + doctrine_type + "_" + trait_groups[trait_group]["levels"][2] + strength[0][1] + " = { is_in_list = selected_doctrines }" + "\n")
                                                    f.write( "\t" + "\t" + "\t" + "\t" + "\t" + "}" +  "\n")
                                                    f.write( "\t" + "\t" + "\t" + "\t" + "\t" + "doctrine:doctrine_" + doctrine_type+ "_" + trait_groups[trait_group]["levels"][3] + strength[0][1] + " = { is_in_list = selected_doctrines }" + "\n")
                                                    f.write( "\t" + "\t" + "\t" + "\t" + "}" + "\n")
                                            f.write( "\t" + "\t" +  "\t" +"}" + "\n")
                                        
                                        #f.write( "\t"+ "\t" + "\t" + "AND = {" + "\n") 
                                        #f.write( "\t"+ "\t" + "\t" + "NOT = { doctrine:" + "doctrine_" + doctrine_type+ "_" + trait_group + "_strong" + " = { is_in_list = selected_doctrines } }" + "\n") #Not strong group
                                        groupStrongQualifier =  "\t"+ "\t" + "\t" + "\t" + "\t" + "doctrine:" + "doctrine_" + doctrine_type+ "_" + trait_group + " = { is_in_list = selected_doctrines }" + "\n"
                                        #f.write( "\t"+ "\t" + "\t" + "}" + "\n")
                                if strength[0][0] == "strong":
                                    f.write( "\t" + "\t" +  "\t" +"custom_description = {" + "\n")
                                    f.write( "\t" + "\t" +  "\t" + "\t" +"text = doctrine_requires_"+doctrine_type+"_trigger" +"\n" )
                                    f.write("\t"+ "\t" + "\t" + "\t" + "OR = {" + "\n")
                                    f.write("\t"+ "\t" + "\t" +  "\t" + "\t" + "doctrine:" + "doctrine_" + doctrine_type + "_" + trait + " = { is_in_list = selected_doctrines }" + "\n")
                                    if (groupStrongQualifier):
                                        f.write(groupStrongQualifier)
                                    f.write("\t"+ "\t" + "\t" + "\t" + "}" + "\n")
                                    f.write("\t"+ "\t" + "\t" + "}" + "\n")
                                f.write( "\t" + "\t" + "}" + "\n")
                                f.write( "\t" + "\t" + "traits = {" + "\n")
                                f.write( "\t" + "\t" + "\t" + doctrine_type + "s = {" + "\n")
                                f.write( "\t" + "\t" + "\t" + "\t" + trait + " = { scale = "+str(strength[2])+" weight = "+str(strength[1][0])+" }" + "\n")
                                #Treat fake Lovers Pox same as real lovers pox
                                if (trait == "lovers_pox"):
                                    if "early_great_pox" in traits:
                                        f.write( "\t" + "\t" + "\t" + "\t" + "early_great_pox" + " = { scale = "+str(strength[2])+" weight = "+str(strength[1][0])+" }" + "\n")
                                f.write( "\t" + "\t" + "\t" + "}" + "\n")
                                f.write( "\t" + "\t" + "}" + "\n")
                                f.write( "\t" + "} " + "\n")
                                f.write( "" + "\n")                            
                        #Localization
                    #Trait Group Doctrines
                    for trait_group in trait_groups:
                        if (not (trait_group in trait_group_blacklist)) and (doctrine_type == "virtue" or not (trait_group in trait_group_sin_blacklist)) and (doctrine_type == "sin" or (not trait_group in trait_group_virtue_blacklist)):
                            for strength in virtue_sin_strength:
                                doctrine_name = "doctrine_" + doctrine_type+ "_" + trait_group + strength[0][1]
                                doctrine_opposite_name = "doctrine_" + opposite_doctrine_type(doctrine_type)+ "_" + trait_group + strength[0][1]
                                f.write( "\t" + doctrine_name + " = {" + "\n")
                                f.write( "\t" + "\t" + "name = {" + "\n")
                                f.write( "\t" + "\t" + "\t" + "first_valid = {" + "\n")
                                f.write( "\t"+ "\t" + "\t" + "\t" + "desc = " + doctrine_name + "_ingame_name" + "\n")
                                f.write( "\t" + "\t" + "\t" + "}" + "\n")
                                f.write( "\t" + "\t" + "}" + "\n")
                                f.write( "\t" + "\t" + "desc = {" + "\n")
                                f.write( "\t" + "\t" + "\t" + "first_valid = {" + "\n")
                                f.write( "\t"+ "\t" + "\t" + "\t" + "desc = " + doctrine_name + "_ingame_desc" + "\n")
                                f.write( "\t" + "\t" + "\t" + "}" + "\n")
                                f.write( "\t" + "\t" + "}" + "\n")
                                f.write( "\t" + "\t" + "piety_cost = {" + "\n")
                                f.write( "\t" + "\t" + "\t" + "value = faith_doctrine_cost_low" + "\n")
                                f.write( "\t" + "\t" + "\t" + "multiply = " + str(len(trait_groups[trait_group]["levels"].values())) + "\n")
                                cost = 0
                                for trait in trait_groups[trait_group]["levels"].values():
                                    for parameter in traits[trait]["parameters"]:
                                        if parameter["name"] == "ruler_designer_cost":
                                            cost += parameter["value"]
                                if doctrine_type == "sin":
                                    f.write( "\t" + "\t" + "\t" + "subtract = " + str(cost) + "\n") #Cheaper to make beneficial things sins
                                else:    
                                    f.write( "\t" + "\t" + "\t" + "add = " + str(cost) + "\n")
                                f.write( "\t" + "\t" + "\t" + "if = {" + "\n")
                                f.write( "\t"+ "\t" + "\t" + "\t" + "limit = { has_doctrine =  " + doctrine_name + " }" + "\n")
                                f.write( "\t"+ "\t" + "\t" + "\t" + "multiply = faith_unchanged_doctrine_cost_mult" + "\n")
                                f.write( "\t" + "\t" + "\t" + "}" + "\n")
                                f.write( "\t" + "\t" + "}" + "\n")
                                f.write( "\t" + "\t" + "is_shown = {" + "\n")
                                f.write( "\t" + "\t" +  "\t" + "always = yes" + "\n") #Default evaluation is and so this is effectively blank
                                if (doctrine_type == "sin" or not (trait_group in trait_group_sin_blacklist)) and (doctrine_type == "virtue" or (not trait_group in trait_group_virtue_blacklist)):
                                    f.write( "\t"+ "\t" + "\t" + "NOT = { doctrine:" + doctrine_opposite_name + " = { is_in_list = selected_doctrines } }" + "\n")
                                f.write( "\t" + "\t" + "}" + "\n")
                                f.write( "\t" + "\t" + "can_pick = {" + "\n")
                                f.write( "\t" + "\t" +  "\t" + "always = yes" + "\n") #Default evaluation is and so this is effectively blank 
                                #Allow to take Strong group if you've taken all weak traits individually. (This is silly but a) symmetry and b) why not?)
                                individualStrongQualifiers =  "\t"+ "\t" + "\t" + "\t" + "AND = {" + "\n"
                                for trait in trait_groups[trait_group]["levels"].values():
                                    #f.write( "\t"+ "\t" + "\t" + "AND = {" + "\n") 
                                    if strength[0][0] == "strong":
                                        individualStrongQualifiers = individualStrongQualifiers +  "\t"+ "\t" + "\t" + "\t" + "\t" + "\t" + "doctrine:" + "doctrine_" + doctrine_type+ "_" + trait  + " = { is_in_list = selected_doctrines }" + "\n"
                                        f.write( "\t" + "\t" + "\t" +"custom_description = {" + "\n")
                                        f.write( "\t" + "\t" + "\t" + "\t" + "text = doctrine_incompatible_strong_"+doctrine_type+"_trigger" +"\n" )
                                        f.write( "\t" + "\t" + "\t" + "\t" + "NOT = { doctrine:" + "doctrine_" + doctrine_type+ "_" + trait + "_strong" + " = { is_in_list = selected_doctrines } }" + "\n") #Not strong trait
                                        f.write( "\t" + "\t" + "\t" + "}" + "\n")

                                        if (doctrine_type == "sin" or not (trait_group in trait_group_sin_blacklist)) and (doctrine_type == "virtue" or (not trait_group in trait_group_virtue_blacklist)):                                        
                                            f.write( "\t" + "\t" + "\t" +"custom_description = {" + "\n")
                                            f.write( "\t" + "\t" + "\t" + "\t" + "text = doctrine_incompatible_weak_"+opposite_doctrine_type(doctrine_type)+"_trigger" +"\n" )
                                            f.write( "\t" + "\t" + "\t" + "\t" + "OR = {" + "\n")
                                            f.write( "\t" + "\t" + "\t" + "\t" + "\t" + "NOT = { doctrine:" + "doctrine_" + opposite_doctrine_type(doctrine_type)+ "_" + trait + " = { is_in_list = selected_doctrines } }" + "\n") #Can't add if weak opposite trait .....
                                            f.write( "\t" + "\t" + "\t" + "\t" + "\t" + "doctrine:" + "doctrine_" + opposite_doctrine_type(doctrine_type)+ "_" + trait + "_strong" + " = { is_in_list = selected_doctrines }" + "\n") #... unless also strong opposite trait
                                            f.write( "\t" + "\t" + "\t" + "\t" +  "}" + "\n")
                                            f.write( "\t" + "\t" + "\t" +"}" + "\n")

                                    else:
                                        f.write( "\t" + "\t" + "\t" +"custom_description = {" + "\n")
                                        f.write( "\t" + "\t" + "\t" + "\t" + "text = doctrine_incompatible_weak_"+doctrine_type+"_trigger" +"\n" )
                                        f.write( "\t" + "\t" + "\t" + "\t" + "OR = {" + "\n") 
                                        f.write( "\t" + "\t" + "\t" + "\t" + "\t" + "NOT = { doctrine:" + "doctrine_" + doctrine_type + "_" + trait + " = { is_in_list = selected_doctrines } }" + "\n") #Can't add if weak trait .....
                                        f.write( "\t" + "\t" + "\t" + "\t" + "\t" + "OR = {" +"\n") 
                                        f.write( "\t" + "\t" + "\t" + "\t" + "\t" + "\t" + "doctrine:" + "doctrine_" + doctrine_type + "_" + trait + "_strong" + " = { is_in_list = selected_doctrines }" + "\n") #... unless also strong trait
                                        f.write( "\t" + "\t" + "\t" + "\t" + "\t" + "\t" + "doctrine:" + "doctrine_" + doctrine_type + "_" + trait_group + "_strong" + " = { is_in_list = selected_doctrines }" + "\n") #...  or strong group
                                        f.write(" \t" + "\t" + "\t" + "\t" + "\t" + "}" + "\n") 
                                        f.write(" \t" + "\t" + "\t" + "\t"+ "}" + "\n") 
                                        f.write( "\t" + "\t" + "\t" + "}" + "\n")
                                    #f.write( "\t"+ "\t" + "\t" + "}" + "\n")

                                if strength[0][0] == "strong":
                                    f.write( "\t" + "\t" + "\t" + "custom_description = {" + "\n")
                                    f.write( "\t" + "\t" + "\t" + "\t" +"text = doctrine_requires_"+doctrine_type+"_trigger" + "\n" )
                                    f.write( "\t" + "\t" + "\t" + "\t" + "OR = {" + "\n")
                                    f.write( "\t" + "\t" + "\t" + "\t" + "\t" + "doctrine:" + "doctrine_" + doctrine_type+ "_" + trait_group + " = { is_in_list = selected_doctrines }" + "\n")
                                    individualStrongQualifiers = individualStrongQualifiers + "\t" + "\t" + "\t" + "\t" + "\t" + "}" + "\n"
                                    f.write(individualStrongQualifiers)
                                    f.write( "\t"+ "\t" + "\t" + "\t" + "}" + "\n")
                                    f.write( "\t" + "\t" +  "\t" +"}" + "\n")

                                f.write( "\t" + "\t" + "}" + "\n")
                                f.write( "\t" + "\t" + "traits = {" + "\n")
                                f.write( "\t" + "\t" + "\t" + doctrine_type + "s = {" + "\n")
                                f.write( "\t" + "\t" + "\t" + "\t" + trait_group + " = { scale = "+str(strength[2])+" weight = "+str(strength[1][1])+" }" + "\n")
                                f.write( "\t" + "\t" + "\t" + "}" + "\n")
                                f.write( "\t" + "\t" + "}" + "\n")
                                f.write( "\t" + "} " + "\n")
                                f.write( "" + "\n")               
                    #Group Equivalent Doctrines
                    for trait_group_equivalent in trait_group_equivalents:
                        if (not (trait_group_equivalent in trait_group_equivalent_blacklist)) and (doctrine_type == "virtue" or not (trait_group_equivalent in trait_group_equivalent_sin_blacklist)) and (doctrine_type == "sin" or not (trait_group_equivalent in trait_group_equivalent_virtue_blacklist)):
                            for strength in virtue_sin_strength:
                                doctrine_name = "doctrine_" + doctrine_type+ "_" + trait_group_equivalent + strength[0][1]
                                doctrine_opposite_name = "doctrine_" + opposite_doctrine_type(doctrine_type)+ "_" + trait_group_equivalent + strength[0][1]
                                f.write( "\t" + doctrine_name + " = {" + "\n")
                                f.write( "\t" + "\t" + "name = {" + "\n")
                                f.write( "\t" + "\t" + "\t" + "first_valid = {" + "\n")
                                f.write( "\t"+ "\t" + "\t" + "\t" + "desc = " + doctrine_name + "_ingame_name" + "\n")
                                f.write( "\t" + "\t" + "\t" + "}" + "\n")
                                f.write( "\t" + "\t" + "}" + "\n")
                                f.write( "\t" + "\t" + "desc = {" + "\n")
                                f.write( "\t" + "\t" + "\t" + "first_valid = {" + "\n")
                                f.write( "\t"+ "\t" + "\t" + "\t" + "desc = " + doctrine_name + "_ingame_desc" + "\n")
                                f.write( "\t" + "\t" + "\t" + "}" + "\n")
                                f.write( "\t" + "\t" + "}" + "\n")
                                f.write( "\t" + "\t" + "piety_cost = {" + "\n")
                                f.write( "\t" + "\t" + "\t" + "value = faith_doctrine_cost_low" + "\n")
                                f.write( "\t" + "\t" + "\t" + "multiply = " + str(len(trait_group_equivalents[trait_group_equivalent]["levels"].values())) + "\n")
                                cost = 0
                                for trait in trait_group_equivalents[trait_group_equivalent]["levels"].values():
                                    for parameter in traits[trait]["parameters"]:
                                        if parameter["name"] == "ruler_designer_cost":
                                            cost += parameter["value"]
                                if doctrine_type == "sin":
                                    f.write( "\t" + "\t" + "\t" + "subtract = " + str(cost) + "\n") #Cheaper to make beneficial things sins
                                else:    
                                    f.write( "\t" + "\t" + "\t" + "add = " + str(cost) + "\n") 
                                f.write( "\t" + "\t" + "\t" + "if = {" + "\n")
                                f.write( "\t"+ "\t" + "\t" + "\t" + "limit = { has_doctrine =  " + doctrine_name + " }" + "\n")
                                f.write( "\t"+ "\t" + "\t" + "\t" + "multiply = faith_unchanged_doctrine_cost_mult" + "\n")
                                f.write( "\t" + "\t" + "\t" + "}" + "\n")
                                f.write( "\t" + "\t" + "}" + "\n")
                                f.write( "\t" + "\t" + "is_shown = {" + "\n")
                                f.write( "\t"+ "\t" + "\t" + "\t" + "NOT = { doctrine:" + doctrine_opposite_name + " = { is_in_list = selected_doctrines } }" + "\n")
                                f.write( "\t" + "\t" + "}" + "\n")
                                f.write( "\t" + "\t" + "can_pick = {" + "\n")
                                f.write( "\t" + "\t" +  "\t" + "always = yes" + "\n") #Default evaluation is and so this is effectively blank 
                                if strength[0][0] == "strong":
                                    f.write( "\t" + "\t" + "\t" + "custom_description = {" + "\n")
                                    f.write( "\t" + "\t" + "\t" + "\t" + "text = doctrine_requires_"+doctrine_type+"_trigger" + "\n" )
                                    f.write( "\t" + "\t" + "\t" + "\t" + "doctrine:" + "doctrine_" + doctrine_type+ "_" + trait_group_equivalent + " = { is_in_list = selected_doctrines }" + "\n")
                                    f.write( "\t" + "\t" + "\t" + "}" + "\n")
                                f.write( "\t" + "\t" + "}" + "\n")
                                f.write( "\t" + "\t" + "traits = {" + "\n")
                                f.write( "\t" + "\t" + "\t" + doctrine_type + "s = {" + "\n")
                                f.write( "\t" + "\t" + "\t" + "\t" + trait_group_equivalent + " = { scale = "+str(strength[2])+" weight = "+str(strength[1][1])+" }" + "\n")
                                f.write( "\t" + "\t" + "\t" + "}" + "\n")
                                f.write( "\t" + "\t" + "}" + "\n")
                                f.write( "\t" + "} " + "\n")
                                f.write( "" + "\n")
                    #Put these at the end because of how Doctrine sorting works, for some reason empties are filled and then the list is sorted for doctrines, unlike tenets which is the reverse
                    #Use an on_game_start to action to fill out all faiths with these doctrines to avoid being autofilled from the start of the list
                    for i in range(1,no_of_slots+1):
                        #Old Empty Doctrine for compatability
                        doctrine_name = "mrsad_empty_"+doctrine_type+"s_" + str(i)
                        f.write( "\t" + doctrine_name + " = {" + "\n")
                        f.write( "\t" + "\t" + "piety_cost = {" + "\n")
                        f.write( "\t" + "\t" + "\t" + "value = 0" + "\n")
                        f.write( "\t" + "\t" + "\t" + "if = {" + "\n")
                        f.write( "\t"+ "\t" + "\t" + "\t" + "limit = { has_doctrine = " + doctrine_name + " }" + "\n")
                        f.write( "\t"+ "\t" + "\t" + "\t" + "multiply = faith_unchanged_doctrine_cost_mult" + "\n")
                        f.write( "\t" + "\t" + "\t" + "}" + "\n")
                        f.write( "\t" + "\t" + "}" + "\n")
                        f.write( "\t" + "\t" + "is_shown = { always = no }" +"\n")
                        f.write( "\t" + "} " + "\n")
                        f.write("" + "\n")

                        #New Empty Doctrine
                        doctrine_name = "doctrine_" + doctrine_type + "_mrsad_empty_"+ str(i)
                        f.write( "\t" + doctrine_name + " = {" + "\n")
                        f.write( "\t" + "\t" + "piety_cost = {" + "\n")
                        f.write( "\t" + "\t" + "\t" + "value = 0" + "\n")
                        f.write( "\t" + "\t" + "\t" + "if = {" + "\n")
                        f.write( "\t"+ "\t" + "\t" + "\t" + "limit = { has_doctrine = " + doctrine_name + " }" + "\n")
                        f.write( "\t"+ "\t" + "\t" + "\t" + "multiply = faith_unchanged_doctrine_cost_mult" + "\n")
                        f.write( "\t" + "\t" + "\t" + "}" + "\n")
                        f.write( "\t" + "\t" + "}" + "\n")
                        f.write("" + "\n")
                        f.write( "\t" + "} " + "\n")
                        f.write("" + "\n")

                    f.write("}"+"\n")

    for language in ["english"]:
        with codecs.open(os.path.join(os.path.join(localization_output_folder,language),localization_output_pre+language+localization_output_end),"w",'utf-8-sig') as f:
            #Localization
            f.write("l_" + language + ":" + "\n")
            f.write("\n")
            f.write(" " + "\n")
            #Empty Tenet Slots 
            for i in range(1,no_of_empty_tenet_slots+1):
                f.write(" " + "tenet_aa_mrsad_empty_" + str(i) + "_name:0 \"\"" +"\n")
                f.write(" " + "tenet_aa_mrsad_empty_" + str(i) + "_desc:0 \"Choose A New Tenet.\"" +"\n")
                f.write(" " +"\n")
            f.write("\n")
            f.write("\n")
            f.write("\n")
            f.write("\n")
                
            for doctrine_type in doctrine_types:
                f.write(" doctrine_mrsad_"+doctrine_type+"s_name:0 \"Additional ["+doctrine_type+"|E]\"" +"\n")
                for i in range(1,no_of_slots+1):
                    if i == 1:
                        f.write("\n")
                        #Old Empty Doctrine for Compatability
                        f.write(" mrsad_empty_"+doctrine_type+"s_"+str(i)+"_name:0 \" \""+"\n")
                        f.write(" mrsad_empty_"+doctrine_type+"s_"+str(i)+"_desc:0 \" \""+"\n")
                        f.write("\n")

                        #New Empty Doctrines
                        f.write(" doctrine_" + doctrine_type+ "_" + "mrsad_empty_"+ str(i)+"_name:0 \"None\""+"\n")
                        f.write(" doctrine_" + doctrine_type+ "_" + "mrsad_empty_"+ str(i)+"_desc:0 \"No additional ["+doctrine_type+"|E]\""+"\n")
                        f.write("\n")

                    else:
                        f.write("\n")
                        #Old Empty Doctrine for Compatability
                        f.write(" mrsad_empty_"+doctrine_type+"s_"+str(i)+"_name:0 \"$mrsad_empty_"+doctrine_type+"s_1_name$\""+"\n")
                        f.write(" mrsad_empty_"+doctrine_type+"s_"+str(i)+"_desc:0 \"$mrsad_empty_"+doctrine_type+"s_1_desc$\""+"\n")
                        f.write("\n")

                        #New Empty Doctrines
                        f.write(" doctrine_" + doctrine_type+ "_mrsad_empty_"+ str(i)+"_name:0 \"$doctrine_" + doctrine_type+ "_" + "mrsad_empty_1_name$\""+"\n")
                        f.write(" doctrine_" + doctrine_type+ "_mrsad_empty_"+ str(i)+"_desc:0 \"$doctrine_" + doctrine_type+ "_" + "mrsad_empty_1_desc$\""+"\n")
                        f.write("\n")

                #Silly work around for GUI Hyperlink issue, even if a conditional name is specified instead. 
                for trait in traits:
                    if not (traits in trait_blacklist):
                        for strength in virtue_sin_strength:
                            #Even more workarounds for weird Paradox Stuff
                            if trait == "viking":
                                f.write(" doctrine_"+doctrine_type+"_"+trait+strength[0][1]+"_name:0 \"$trait_"+"viking_fallback"+"$"+strength[0][3]+"\""+"\n")
                            elif trait == "child_of_concubine_male":
                                f.write(" doctrine_"+doctrine_type+"_"+trait+strength[0][1]+"_name:0 \"$trait_"+"child_of_concubine"+"$"+strength[0][3]+"\""+"\n")
                            elif trait == "child_of_concubine_female":
                                f.write(" doctrine_"+doctrine_type+"_"+trait+strength[0][1]+"_name:0 \"$trait_"+"child_of_concubine"+"$"+strength[0][3]+"\""+"\n")
                            elif trait == "shieldmaiden":
                                f.write(" doctrine_"+doctrine_type+"_"+trait+strength[0][1]+"_name:0 \"$trait_"+"shieldmaiden_female"+"$"+strength[0][3]+"\""+"\n")
                            else:
                                f.write(" doctrine_"+doctrine_type+"_"+trait+strength[0][1]+"_name:0 \"$trait_"+trait+"$"+strength[0][3]+"\""+"\n")
                            f.write(" doctrine_"+doctrine_type+"_"+trait+strength[0][1]+"_desc:0 \"$doctrine_"+doctrine_type+"_"+trait+"_name$ should be a"+ strength[0][2] +" ["+doctrine_type+"|E]\""+"\n")
                for trait_group in trait_groups:
                    if not (trait_group in trait_group_blacklist):
                        for strength in virtue_sin_strength:
                            f.write(" doctrine_"+doctrine_type+"_"+trait_group+strength[0][1]+"_name:0 \"$trait_"+trait_group+"$"+strength[0][3]+"\""+"\n")
                            f.write(" doctrine_"+doctrine_type+"_"+trait_group+strength[0][1]+"_desc:0 \"$doctrine_"+doctrine_type+"_"+trait_group+"_name$ should be a"+ strength[0][2] +" ["+doctrine_type+"|E]\""+"\n")
                for trait_group_equivalent in trait_group_equivalents:
                    if not (trait_group_equivalent in trait_group_equivalent_blacklist):
                        for strength in virtue_sin_strength:
                            f.write(" doctrine_"+doctrine_type+"_"+trait_group_equivalent+strength[0][1]+"_name:0 \"$trait_"+trait_group_equivalent+"$"+strength[0][3]+"\""+"\n")
                            f.write(" doctrine_"+doctrine_type+"_"+trait_group_equivalent+strength[0][1]+"_desc:0 \"$doctrine_"+doctrine_type+"_"+trait_group_equivalent+"_name$ should be a" + strength[0][2] + " ["+doctrine_type+"|E]\""+"\n")
                f.write("\n")

                #Doctrines
                for trait in traits:                    
                    if not (trait in trait_blacklist):
                        for strength in virtue_sin_strength:
                            f.write(" doctrine_"+doctrine_type+"_"+trait+strength[0][1]+"_ingame_name:0 \"[GetTrait('"+trait+"').GetName( GetNullCharacter )]"+strength[0][3]+"\""+"\n")
                            f.write(" doctrine_"+doctrine_type+"_"+trait+strength[0][1]+"_ingame_desc:0 \"$doctrine_"+doctrine_type+"_"+trait+"_ingame_name$ should be a" + strength[0][2] + " ["+doctrine_type+"|E]\""+"\n")
                for trait_group in trait_groups:
                    if not (trait_group in trait_group_blacklist):
                        for strength in virtue_sin_strength:
                            f.write(" doctrine_"+doctrine_type+"_"+trait_group+strength[0][1]+"_ingame_name:0 \"[GetTraitGroup('"+trait_group+"').GetName()]"+strength[0][3]+"\""+"\n")
                            f.write(" doctrine_"+doctrine_type+"_"+trait_group+strength[0][1]+"_ingame_desc:0 \"$doctrine_"+doctrine_type+"_"+trait_group+"_ingame_name$ should be a" + strength[0][2] + " ["+doctrine_type+"|E]\""+"\n")
                for trait_group_equivalent in trait_group_equivalents:
                    if not (trait_group_equivalent in trait_group_equivalent_blacklist):
                        for strength in virtue_sin_strength:
                            f.write(" doctrine_"+doctrine_type+"_"+trait_group_equivalent+strength[0][1]+"_ingame_name:0 \"[GetTraitGroup('"+trait_group_equivalent+"').GetName()]"+strength[0][3]+"\""+"\n")
                            f.write(" doctrine_"+doctrine_type+"_"+trait_group_equivalent+strength[0][1]+"_ingame_desc:0 \"$doctrine_"+doctrine_type+"_"+trait_group_equivalent+"_ingame_name$ should be a" + strength[0][2] + " ["+doctrine_type+"|E]\""+"\n")
                f.write("\n")
            f.write("\n")

    #Tenets
    with codecs.open(tenets_source,"r",'utf-8-sig') as f,codecs.open(os.path.join(doctrine_output_folder,tenets_output),"w",'utf-8-sig') as g:
        e = f.read()
        elines = e.splitlines(True)
        #Copy opener
        preamble = elines[0:2]
        g.writelines(preamble)
        #Get default number of picks (in case tenets are from a mod that has eg default 4 tenets per faith)
        sp_raw = regex.search(slot_picks_regex,e)
        if sp_raw:
            no_of_picks = int(sp_raw.capturesdict()['sp_value'][0],10)
        else:
            no_of_picks = default_picks
        g.write("\t"+"number_of_picks = "+str(no_of_empty_tenet_slots+no_of_picks)+"\n")
        g.write("\n")
        g.write("\t"+"#############################"+"\n")
        g.write("\t"+"# Empty Tenets              #"+"\n")
        g.write("\t"+"#############################"+"\n")
        g.write("\n")

        #Dynamic Tenets
        for i in range(1,no_of_empty_tenet_slots+1):
            #Tenets have _aa_ to float them to the top of the list (because Tenets in the list as sorted by alphabetical order of the underlting tnenet name (probably to keep eg Endura / Ritual Sucicide in the same location))
            #Theoretically shouldn't need backwards compatability because these tenets should never exist in game at the point the game can be saved.
            doctrine_name = "tenet_aa_mrsad_empty_" + str(i)
            g.write("\t" + doctrine_name + " = {" + "\n")
            g.write("\t" + "\t" + "icon = mrsad_tenet" + "\n")
            g.write("\t" + "\t" + "piety_cost = {" + "\n")
            g.write("\t" + "\t" + "\t" + "value = 0" + "\n")
            g.write("\t" + "\t" + "}" + "\n")
            g.write( "\t" + "} " + "\n")
            g.write( "" + "\n")
        #Standard Tenets + close
        postlude = elines[3:]
        g.writelines(postlude)
    #Events
    with codecs.open(os.path.join(events_output_folder,creation_event_output),"w",'utf-8-sig') as f:
        f.write("namespace = faith_creation_mrsad"+"\n")
        f.write("\n")
        f.write("faith_creation_mrsad.001 = {"+"\n")
        f.write("\t"+"hidden = yes"+"\n")
        f.write("\n")
        f.write("\t"+"trigger = {"+"\n")
        f.write("\t"+"\t"+"always = yes"+"\n")
        f.write("\t"+"}"+"\n")
        f.write("\n")
        f.write("\t"+"immediate = {"+"\n")
        f.write("\t"+"\t"+"faith = {"+"\n")
        for i in range(1,no_of_empty_tenet_slots+1):
            doctrine_name = "tenet_aa_mrsad_empty_" + str(i)
            f.write("\t"+"\t"+"\t"+"if = {"+"\n")
            f.write("\t"+"\t"+"\t"+"\t"+"limit = {"+"\n")
            f.write("\t"+"\t"+"\t"+"\t"+"\t"+"has_doctrine = "+doctrine_name+"\n")
            f.write("\t"+"\t"+"\t"+"\t"+"}"+"\n")
            f.write("\t"+"\t"+"\t"+"\t"+"remove_doctrine = "+doctrine_name+"\n")
            f.write("\t"+"\t"+"\t"+"}"+"\n")
        f.write("\t"+"\t"+"}"+"\n")
        f.write("\t"+"}"+"\n")
        f.write("}"+"\n")
    #Game Start Efffect
    with codecs.open(os.path.join(scripted_effects_output_folder,startup_effects_output),"w",'utf-8-sig') as f:
        f.write("mrsad_virtues_sins_setup_effect = {"+"\n")
        f.write("\t"+"if = {"+"\n")
        f.write("\t"+"\t"+"limit = { # Double-check to make certain this should happen"+"\n")
        f.write("\t"+"\t"+"\t"+"NOT = { exists = global_var:mrsad_flag_virtue_sins_setup }"+"\n")
        f.write("\t"+"\t"+"}"+"\n")
        f.write("\t"+"\t"+"set_global_variable = { # Add global variable to prevent this from happening more than once"+"\n")
        f.write("\t"+"\t"+"\t"+"name = mrsad_flag_virtue_sins_setup"+"\n")
        f.write("\t"+"\t"+"\t"+"value = yes"+"\n")
        f.write("\t"+"\t"+"}"+"\n")
        f.write("\t"+"\t"+"every_religion_global = {"+"\n")
        f.write("\t"+"\t"+"\t"+"every_faith = {"+"\n")
        for doctrine_type in doctrine_types:
            for i in range(1,no_of_slots+1):
                f.write("\t"+"\t"+"\t"+"\t"+"add_doctrine = doctrine_" + doctrine_type + "_mrsad_empty_" + str(i) +"\n")
        f.write("\t"+"\t"+"\t"+"}"+"\n")
        f.write("\t"+"\t"+"}"+"\n")
        f.write("\t"+"}"+"\n")
        f.write("}"+"\n")



    
if __name__ == "__main__":
    main()