-- Removes this pack's looks. Run by hand (the server never applies data/sql/uninstall), on
-- acore_world and acore_characters as marked. Players can keep patch-R: unused displays do nothing.

-- acore_world
DELETE FROM `mod_transmog_plus_forms` WHERE `Form` IN ('bear', 'cat', 'travel', 'aquatic', 'flight', 'moonkin', 'tree');
DELETE m FROM `creature_template_model` m JOIN `creature_template` t ON t.`entry` = m.`CreatureID`
WHERE t.`entry` BETWEEN 9501000 AND 9501499 AND t.`subname` = 'Druid Form';
DELETE t FROM `creature_template` t WHERE t.`entry` BETWEEN 9501000 AND 9501499 AND t.`subname` = 'Druid Form';
DELETE FROM `creature_model_info` WHERE `DisplayID` BETWEEN 95000 AND 95999;
DELETE FROM `creaturedisplayinfo_dbc` WHERE `ID` BETWEEN 95000 AND 95999;
DELETE FROM `creaturemodeldata_dbc` WHERE `ID` BETWEEN 9500 AND 9599;

-- acore_characters: the looks characters picked from this pack
-- DELETE FROM `mod_transmog_plus_form_choice` WHERE `Form` BETWEEN 0 AND 6;
