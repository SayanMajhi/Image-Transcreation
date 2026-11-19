# Florence and SmolVLM model-selection diagnostic

11-image exploratory convenience sample (10 photographs and one market illustration), not a benchmark or verified cultural ground truth. Groups and source titles are provenance metadata, never inference inputs. Public photos may overlap model training data; generalization is not established.

## Objective resource measurements

| Model | Images | Median ms | Mean ms | Maximum peak CUDA MiB | At token ceiling | Suspected truncations |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| smolvlm | 11 | 5617.28 | 5127.57 | 1124.13 | 5 | 5 |
| florence | 11 | 663.77 | 737.90 | 609.95 | 0 | 0 |

## Sanity images (excluded from collection metrics)

### smolvlm

[Inspect simple sanity image](../../../../data/vlm_collection/sanity_cats.png)

Two tabby cats are sleeping on a pink blanket. One cat is curled up with its head on the other cat&#x27;s back.

Manual sanity assessment: __________

### florence

[Inspect simple sanity image](../../../../data/vlm_collection/sanity_cats.png)

There are two cats laying on a pink blanket. There are remotes next to the cats. The cats are brown and black.

Manual sanity assessment: __________

## Experimental limitations

- Exploratory convenience sample, not a held-out benchmark. Possible overlap with training data.
- SmolVLM uses a fixed uncertainty-aware instruction and its native processor chat template. Florence retains its configured MORE_DETAILED_CAPTION task and native task expansion.
- SmolVLM uses greedy decoding (one beam), SDPA, generation caching and a 1024-pixel longest-edge processor setting with image splitting. Florence retains three beams, eager attention, disabled caching and its original processor. These are different operating points.
- Token counts use different tokenizers and are not equivalent measures of information or accuracy.
- A common 128-token ceiling can truncate verbose outputs. Inspect ceiling/EOS flags and the reported counts; incomplete captions limit omission and relationship comparisons.
- One timed observation per image after one unrelated sanity/warmup image per model. Loading and file reading are excluded. Timing includes processor work, transfers, generation and decoding. Peak allocated CUDA memory includes resident weights, not total driver memory.
- No automatic winner or cultural correctness score. Manual review must separate visible object recognition from specific identity claims. Caption length is not an accuracy metric.

Exact instruction/task text, formatted prompts, processor settings, seed, device, precision, library versions and per-image measurements are recorded in comparison.json.

## Manual scoring

All scores start blank. For object coverage and relationship accuracy: 0 = poor, 1 = limited, 2 = mostly correct, 3 = strong visible support. For important omissions: 0 = severe, 1 = several, 2 = minor, 3 = none observed. For hallucinations: 0 = severe, 1 = several unsupported claims, 2 = minor, 3 = none observed. Use N/A or Uncertain when appropriate. List concrete evidence and claims. Score visible object appearance separately from culturally specific identity. A model mention or a source title is not proof of correctness.

| Image | Model | Object coverage 0–3 | Relationship accuracy 0–3 | Important omissions 0–3 | Hallucinations 0–3 | Visible evidence / claims | Cultural identity judgment / verification needed |
| --- | --- | --- | --- | --- | --- | --- | --- |
| scene_01 | smolvlm | | | | | | |
| scene_01 | florence | | | | | | |
| scene_02 | smolvlm | | | | | | |
| scene_02 | florence | | | | | | |
| scene_03 | smolvlm | | | | | | |
| scene_03 | florence | | | | | | |
| scene_04 | smolvlm | | | | | | |
| scene_04 | florence | | | | | | |
| scene_05 | smolvlm | | | | | | |
| scene_05 | florence | | | | | | |
| scene_06 | smolvlm | | | | | | |
| scene_06 | florence | | | | | | |
| scene_07 | smolvlm | | | | | | |
| scene_07 | florence | | | | | | |
| scene_08 | smolvlm | | | | | | |
| scene_08 | florence | | | | | | |
| scene_09 | smolvlm | | | | | | |
| scene_09 | florence | | | | | | |
| scene_10 | smolvlm | | | | | | |
| scene_10 | florence | | | | | | |
| scene_11 | smolvlm | | | | | | |
| scene_11 | florence | | | | | | |

## scene_01 (cultural sampling group)

[Inspect original input](../../../../data/sample_images/durga.jpg)

SHA-256: `c43e0c3f07b88a310d0e120e7aa32ea5a29cecba37747015bcdec75c284e5ab0`

**smolvlm:** The image depicts a large, ornate, and colorful deity, likely a Hindu goddess, prominently featured in the center of the image. The deity is seated on a throne, with its arms outstretched, and is surrounded by a large, swirling, and billowing cloud of smoke. The goddess is adorned with elaborate jewelry, including a large, ornate headdress, and a richly decorated skirt. Her body is adorned with multiple arms, each holding a different object, which may represent various aspects of the goddess&#x27;s power or attributes.

The goddess is surrounded by a group of people, some of whom are holding objects, likely offerings

Generated tokens: 128; ceiling reached: True; EOS reached: False

**florence:** A group of women are dancing together. They are all dressed in traditional Indian garb. One of the women is in the middle of the group dancing. She is wearing a colorful garb and headdress. The women are holding brown bowls in their hands. There is smoke coming out of the bowls. There are wires hanging above the women.

Generated tokens: 71; ceiling reached: False; EOS reached: not recorded for the unchanged Florence caption result


## scene_02 (cultural sampling group)

[Inspect original input](../../../../data/vlm_collection/scene_02.jpg)

SHA-256: `321c415a72e47d745949c90170c6342f70dafcbbe47380ff4cfaffbaf2b4dfc2`

**smolvlm:** In the image there are a lot of diyas placed on the floor.

Generated tokens: 16; ceiling reached: False; EOS reached: True

**florence:** There are several small candles on the ground. There are small white rocks under the candles. There is a small gold bowl in the middle of the rocks.

Generated tokens: 34; ceiling reached: False; EOS reached: not recorded for the unchanged Florence caption result


## scene_03 (cultural sampling group)

[Inspect original input](../../../../data/vlm_collection/scene_03.jpg)

SHA-256: `12ad692ef221e14113160a2f1be5365dc68f316c4fe98af0deb7e1a4319f00d0`

**smolvlm:** A large, colorful lion costume is being worn by a group of people in a street. The costume is yellow, red, and gold, and it has a large, round head with a red nose and two large, yellow eyes. The costume has a long, curling tail, and the arms are outstretched to the sides. The people wearing the costume are standing on a street, and there are other people standing in the background. There are buildings in the background, and the sky is blue with some scattered clouds.

Generated tokens: 106; ceiling reached: False; EOS reached: True

**florence:** There is a person in a large yellow and red costume. They are standing in the middle of the street. There are people standing behind them watching them.

Generated tokens: 34; ceiling reached: False; EOS reached: not recorded for the unchanged Florence caption result


## scene_04 (cultural sampling group)

[Inspect original input](../../../../data/vlm_collection/scene_04.jpg)

SHA-256: `8c1b1a8880238c03d1f056a12d27d7b46e8d20bcc518b230ae105c0c977403ab`

**smolvlm:** A woman kneels on a table in front of a tea pot and a dish of food. There is an umbrella behind her. There are red tablecloths on the seating area. There are trees behind the seating area.

Generated tokens: 46; ceiling reached: False; EOS reached: True

**florence:** A woman is wearing a brown dress. She is sitting in front of a table. There is a red umbrella over the table.

Generated tokens: 29; ceiling reached: False; EOS reached: not recorded for the unchanged Florence caption result


## scene_05 (cultural sampling group)

[Inspect original input](../../../../data/vlm_collection/scene_05.jpg)

SHA-256: `3f38b0c2934d7e395700966b6b258de4a7fdbf613f17e6cb84758a327bbddd99`

**smolvlm:** The image depicts a vibrant and colorful table setup, likely intended for a festive or celebratory occasion. The table is covered with a yellow tablecloth, which is complemented by a colorful patterned drape that includes shades of purple, yellow, and red. The table is also adorned with various fruits and vegetables, arranged in a visually appealing manner.

Starting from the top, there is a framed photograph of a person, likely a family member or close friend, positioned in the center of the table. The photograph is bordered by a decorative frame, adding a touch of elegance to the setup. Below the photograph, there is a bowl filled with

Generated tokens: 128; ceiling reached: True; EOS reached: False

**florence:** There is a table with a yellow table cloth on it. There is a picture hanging on the wall behind the table. There are flowers in vases on the table in front of the flowers.

Generated tokens: 42; ceiling reached: False; EOS reached: not recorded for the unchanged Florence caption result


## scene_06 (ordinary sampling group)

[Inspect original input](../../../../data/vlm_collection/scene_06.jpg)

SHA-256: `e0fa05019d587cc62b1d4d5a82d7440216b5d88ef0f2149a69f2eb2ee640fca0`

**smolvlm:** A medium outdoor shot shows a row of black doors with graffiti on them, a bicycle leaning against the sidewalk in front of the doors, and a brick sidewalk in the foreground. The doors are framed by a white wall, and the graffiti on the doors includes a blue cat, the word &quot;AGAN&quot; in white, and the word &quot;Lane&quot; in white. The bicycle is a standard two-wheeled bike with a black frame and blue seat. The sidewalk is made of red bricks, and the bricks are laid in a herringbone pattern.

Generated tokens: 112; ceiling reached: False; EOS reached: True

**florence:** A bicycle is parked in front of a building. The building is covered in graffiti. The graffiti is colorful. There are three doors on the building.

Generated tokens: 33; ceiling reached: False; EOS reached: not recorded for the unchanged Florence caption result


## scene_07 (ordinary sampling group)

[Inspect original input](../../../../data/vlm_collection/scene_07.jpg)

SHA-256: `7eabd572dd34109dffc90c4ba7a60863a01fadd2f070c77dbfe7cb88636d6d7a`

**smolvlm:** The image depicts a cozy, rustic interior of a traditional house. The room is dimly lit, with a warm orange hue, suggesting that it is either early morning or late afternoon. The walls are made of rough-hewn stone, giving the space a rustic and homely feel. The ceiling is made of wooden beams, adding to the rustic charm of the room.

In the center of the room, there is a small, round, glowing fire pit. The fire pit is surrounded by a few items: a few metal pots and pans, a small bowl, and a few other objects that appear to be cooking utensils.

Generated tokens: 128; ceiling reached: True; EOS reached: False

**florence:** A man is sitting in front of a fire. The man is wearing a checkered shirt. There is a shelf above the man with utensils on it.

Generated tokens: 37; ceiling reached: False; EOS reached: not recorded for the unchanged Florence caption result


## scene_08 (ordinary sampling group)

[Inspect original input](../../../../data/vlm_collection/scene_08.jpg)

SHA-256: `249a8c34530c2c5d68d266372b787401e2197bc0e8faa0b57b21735082e1fa1c`

**smolvlm:** In an outdoor setting, a group of young men are playing soccer on a stone-paved area. One of the players is in a blue shirt with the number 38 on the back. The player is stretching out his body with one arm extended towards the ball. Another player is in a white shirt with a blue and black graphic on the back. The player in the white shirt is looking at the player in the blue shirt. The player in the blue shirt is looking at the ball. The player in the white shirt has his arms extended out to the sides. The player in the blue shirt has his arms extended out to the

Generated tokens: 128; ceiling reached: True; EOS reached: False

**florence:** A group of boys are playing soccer outside on a sunny day. Two of the boys are wearing blue shirts and shorts. One boy is laying on the ground trying to kick the ball. A group of people can be seen standing on a sidewalk behind the boys. A tall brick building is standing near the people.

Generated tokens: 64; ceiling reached: False; EOS reached: not recorded for the unchanged Florence caption result


## scene_09 (ordinary sampling group)

[Inspect original input](../../../../data/vlm_collection/scene_09.jpg)

SHA-256: `91348a0926e75d082f6298d13db9fb82b2a6d6934ecbd5d52b2cb16854db119a`

**smolvlm:** The image depicts a scene of a kitchen or cooking area. The primary objects in the image include:

1. **People**: There are three individuals in the image. 
   - **Person in the Front**: This person is standing and appears to be holding a large bowl or container. The person is wearing a long, dark-colored garment, possibly a skirt or a long coat.
   - **Person Behind the Person in the Front**: This person is standing behind the person in the front. They are wearing a light-colored garment, possibly a shirt or a jacket.
   - **Person Behind the Person Behind the Person**: This

Generated tokens: 128; ceiling reached: True; EOS reached: False

**florence:** A painting of people standing around a table. There are baskets on the table in front of them. There is a woman in a red dress standing next to the table.

Generated tokens: 37; ceiling reached: False; EOS reached: not recorded for the unchanged Florence caption result


## scene_10 (ordinary sampling group)

[Inspect original input](../../../../data/vlm_collection/scene_10.jpg)

SHA-256: `2fb7febc73bf3113266c6ff2a0fe21159efa440f6dee8c858b2c72ef6a375643`

**smolvlm:** An aerial shot of the Netherlands. The river IJsselmeer is on the left side of the image, and the IJsselmeer is on the right side. The IJsselmeer is a large river that flows from the North Sea to the South Sea. The Netherlands is a country in Western Europe. The Netherlands is known for its canals. The canals are a major feature of the Netherlands. The Netherlands is a country that is known for its architecture. The architecture is a mix of Dutch and European styles.

Generated tokens: 111; ceiling reached: False; EOS reached: True

**florence:** This is an aerial view of a city. The sky is blue with white fluffy clouds. The water is blue and calm. The land is brown. There are many buildings and houses on the land.

Generated tokens: 42; ceiling reached: False; EOS reached: not recorded for the unchanged Florence caption result


## scene_11 (ordinary sampling group)

[Inspect original input](../../../../data/vlm_collection/scene_11.jpg)

SHA-256: `3dae75e7e6274c66ed235f4cc675dd71c949d3d198debd24c8628984daa7ec7d`

**smolvlm:** A train station with two trains parked facing away from the viewer. The train on the right is a blue train with a red sign on top of it. The train on the left is a white train with a blue stripe along the side. There is a pole in the foreground with a sign on it that says &quot;1&quot;. There is snow on the ground. The sky is dark with a thick, dark cloud above the station.

Generated tokens: 87; ceiling reached: False; EOS reached: True

**florence:** Two blue and white trains are parked at a train station at night. There is a light pole in front of the platform with a sign on it.

Generated tokens: 33; ceiling reached: False; EOS reached: not recorded for the unchanged Florence caption result

Reviewer: __________  Date: __________

Manual model-selection conclusion: __________
