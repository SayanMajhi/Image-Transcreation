# Saved VLM comparison outputs

SmolVLM-500M is the selected application model. This file preserves the required experimental outputs; interpretation is in [model_comparison.md](model_comparison.md). No inference was rerun during consolidation.

These are model-generated claims, not verified descriptions. Manual quality scores were never filled in. BLIP was tested on the original image only; it was not part of the eleven-image paired run.

## Checkpoints and settings

| Model | Resolved revision | Original settings |
| --- | --- | --- |
| BLIP base | `82a37760796d32b1411fe092ab5d4e227313294b` | 64 tokens; three beams; cache enabled |
| Florence-2 base-ft | `f6c1a25888ffc1d945ee8a1a77ac833c7303d46e` | 128 tokens; three beams; MORE_DETAILED_CAPTION; eager attention; cache disabled |
| SmolVLM-500M-Instruct | `a7da5b986cb59b408707209984f360a5f4ad7e47` | 128 tokens; greedy; SDPA; cache enabled; 1024-pixel longest edge; image splitting |

Recorded environment: CUDA FP16, seed 42, PyTorch 2.15.0+cu132, Transformers 4.57.6. Full model IDs, prompts, frozen configuration, image hashes and provenance remain in the raw archive.

## Original paired run: measured resources

| Model | Images | Median inference ms | Mean inference ms | Maximum peak CUDA MiB | Token ceilings reached |
| --- | ---: | ---: | ---: | ---: | ---: |
| smolvlm | 11 | 5617.28 | 5127.57 | 1124.13 | 5 |
| florence | 11 | 663.77 | 737.90 | 609.95 | 0 |

The paired run followed one sanity/warmup image per model. Inference includes preprocessing, transfers, generation and decoding; excludes loading and file reading. Peak CUDA allocation includes resident weights, not total driver memory.

## Original single-image baseline

Input SHA-256: `c43e0c3f07b88a310d0e120e7aa32ea5a29cecba37747015bcdec75c284e5ab0`; dimensions: [980, 692].

**BLIP**

> a woman dressed as deity performs during festival

1222.89 ms.

**Florence-2**

> A group of women are dancing together. They are all dressed in traditional Indian garb. One of the women is in the middle of the group dancing. She is wearing a colorful garb and headdress. The women are holding brown bowls in their hands. There is smoke coming out of the bowls. There are wires hanging above the women.

3466.74 ms.

## Eleven-image paired captions

11-image exploratory convenience sample (10 photographs and one market illustration), not a benchmark or verified cultural ground truth. Groups and source titles are provenance metadata, never inference inputs. Public photos may overlap model training data; generalization is not established.

### scene_01 (cultural)

Input SHA-256: `c43e0c3f07b88a310d0e120e7aa32ea5a29cecba37747015bcdec75c284e5ab0`; dimensions: [980, 692].

Source: User-provided local photograph; public provenance unspecified

License: Unspecified; local research use

**smolvlm**

> The image depicts a large, ornate, and colorful deity, likely a Hindu goddess, prominently featured in the center of the image. The deity is seated on a throne, with its arms outstretched, and is surrounded by a large, swirling, and billowing cloud of smoke. The goddess is adorned with elaborate jewelry, including a large, ornate headdress, and a richly decorated skirt. Her body is adorned with multiple arms, each holding a different object, which may represent various aspects of the goddess's power or attributes.
> 
> The goddess is surrounded by a group of people, some of whom are holding objects, likely offerings

128 generated tokens; EOS: False; token ceiling: True; 5978.22 ms.

**florence**

> A group of women are dancing together. They are all dressed in traditional Indian garb. One of the women is in the middle of the group dancing. She is wearing a colorful garb and headdress. The women are holding brown bowls in their hands. There is smoke coming out of the bowls. There are wires hanging above the women.

71 generated tokens; 1196.02 ms.

### scene_02 (cultural)

Input SHA-256: `321c415a72e47d745949c90170c6342f70dafcbbe47380ff4cfaffbaf2b4dfc2`; dimensions: [1280, 842].

Source: https://commons.wikimedia.org/wiki/File:Diwali_Oil_lamps_Darjeeling.jpg

License: CC BY-SA 3.0

**smolvlm**

> In the image there are a lot of diyas placed on the floor.

16 generated tokens; EOS: True; token ceiling: False; 1103.17 ms.

**florence**

> There are several small candles on the ground. There are small white rocks under the candles. There is a small gold bowl in the middle of the rocks.

34 generated tokens; 538.47 ms.

### scene_03 (cultural)

Input SHA-256: `12ad692ef221e14113160a2f1be5365dc68f316c4fe98af0deb7e1a4319f00d0`; dimensions: [1280, 1443].

Source: https://commons.wikimedia.org/wiki/File:Chinese_New_Year_Lion_Dance.jpg

License: CC BY 2.0

**smolvlm**

> A large, colorful lion costume is being worn by a group of people in a street. The costume is yellow, red, and gold, and it has a large, round head with a red nose and two large, yellow eyes. The costume has a long, curling tail, and the arms are outstretched to the sides. The people wearing the costume are standing on a street, and there are other people standing in the background. There are buildings in the background, and the sky is blue with some scattered clouds.

106 generated tokens; EOS: True; token ceiling: False; 5060.27 ms.

**florence**

> There is a person in a large yellow and red costume. They are standing in the middle of the street. There are people standing behind them watching them.

34 generated tokens; 651.70 ms.

### scene_04 (cultural)

Input SHA-256: `8c1b1a8880238c03d1f056a12d27d7b46e8d20bcc518b230ae105c0c977403ab`; dimensions: [1280, 960].

Source: https://commons.wikimedia.org/wiki/File:Japan_tea_ceremony_1165.jpg

License: CC BY-SA 4.0

**smolvlm**

> A woman kneels on a table in front of a tea pot and a dish of food. There is an umbrella behind her. There are red tablecloths on the seating area. There are trees behind the seating area.

46 generated tokens; EOS: True; token ceiling: False; 2342.52 ms.

**florence**

> A woman is wearing a brown dress. She is sitting in front of a table. There is a red umbrella over the table.

29 generated tokens; 463.34 ms.

### scene_05 (cultural)

Input SHA-256: `3f38b0c2934d7e395700966b6b258de4a7fdbf613f17e6cb84758a327bbddd99`; dimensions: [1280, 1912].

Source: https://commons.wikimedia.org/wiki/File:Altardediademuertos.jpg

License: CC BY 2.0

**smolvlm**

> The image depicts a vibrant and colorful table setup, likely intended for a festive or celebratory occasion. The table is covered with a yellow tablecloth, which is complemented by a colorful patterned drape that includes shades of purple, yellow, and red. The table is also adorned with various fruits and vegetables, arranged in a visually appealing manner.
> 
> Starting from the top, there is a framed photograph of a person, likely a family member or close friend, positioned in the center of the table. The photograph is bordered by a decorative frame, adding a touch of elegance to the setup. Below the photograph, there is a bowl filled with

128 generated tokens; EOS: False; token ceiling: True; 7655.52 ms.

**florence**

> There is a table with a yellow table cloth on it. There is a picture hanging on the wall behind the table. There are flowers in vases on the table in front of the flowers.

42 generated tokens; 685.36 ms.

### scene_06 (ordinary)

Input SHA-256: `e0fa05019d587cc62b1d4d5a82d7440216b5d88ef0f2149a69f2eb2ee640fca0`; dimensions: [1280, 966].

Source: https://commons.wikimedia.org/wiki/File:Parked_bicycle_with_graffitied_building_facade_and_doors_in_Amsterdam.jpg

License: CC BY-SA 4.0

**smolvlm**

> A medium outdoor shot shows a row of black doors with graffiti on them, a bicycle leaning against the sidewalk in front of the doors, and a brick sidewalk in the foreground. The doors are framed by a white wall, and the graffiti on the doors includes a blue cat, the word "AGAN" in white, and the word "Lane" in white. The bicycle is a standard two-wheeled bike with a black frame and blue seat. The sidewalk is made of red bricks, and the bricks are laid in a herringbone pattern.

112 generated tokens; EOS: True; token ceiling: False; 5617.28 ms.

**florence**

> A bicycle is parked in front of a building. The building is covered in graffiti. The graffiti is colorful. There are three doors on the building.

33 generated tokens; 1009.67 ms.

### scene_07 (ordinary)

Input SHA-256: `7eabd572dd34109dffc90c4ba7a60863a01fadd2f070c77dbfe7cb88636d6d7a`; dimensions: [1280, 914].

Source: https://commons.wikimedia.org/wiki/File:Grandmother_preparing_food_inside_traditional_kitchen_(edited).jpg

License: CC BY-SA 4.0

**smolvlm**

> The image depicts a cozy, rustic interior of a traditional house. The room is dimly lit, with a warm orange hue, suggesting that it is either early morning or late afternoon. The walls are made of rough-hewn stone, giving the space a rustic and homely feel. The ceiling is made of wooden beams, adding to the rustic charm of the room.
> 
> In the center of the room, there is a small, round, glowing fire pit. The fire pit is surrounded by a few items: a few metal pots and pans, a small bowl, and a few other objects that appear to be cooking utensils.

128 generated tokens; EOS: False; token ceiling: True; 6192.10 ms.

**florence**

> A man is sitting in front of a fire. The man is wearing a checkered shirt. There is a shelf above the man with utensils on it.

37 generated tokens; 731.33 ms.

### scene_08 (ordinary)

Input SHA-256: `249a8c34530c2c5d68d266372b787401e2197bc0e8faa0b57b21735082e1fa1c`; dimensions: [1280, 835].

Source: https://commons.wikimedia.org/wiki/File:Boys_playing_street_football_in_Egypt.jpg

License: CC BY-SA 4.0

**smolvlm**

> In an outdoor setting, a group of young men are playing soccer on a stone-paved area. One of the players is in a blue shirt with the number 38 on the back. The player is stretching out his body with one arm extended towards the ball. Another player is in a white shirt with a blue and black graphic on the back. The player in the white shirt is looking at the player in the blue shirt. The player in the blue shirt is looking at the ball. The player in the white shirt has his arms extended out to the sides. The player in the blue shirt has his arms extended out to the

128 generated tokens; EOS: False; token ceiling: True; 6218.50 ms.

**florence**

> A group of boys are playing soccer outside on a sunny day. Two of the boys are wearing blue shirts and shorts. One boy is laying on the ground trying to kick the ball. A group of people can be seen standing on a sidewalk behind the boys. A tall brick building is standing near the people.

64 generated tokens; 887.51 ms.

### scene_09 (ordinary)

Input SHA-256: `91348a0926e75d082f6298d13db9fb82b2a6d6934ecbd5d52b2cb16854db119a`; dimensions: [1280, 897].

Source: https://commons.wikimedia.org/wiki/File:John_Frederick_Tayler_-_A_Fruit_Stall_in_a_Market_-_B1975.4.952_-_Yale_Center_for_British_Art.jpg

License: CC0

**smolvlm**

> The image depicts a scene of a kitchen or cooking area. The primary objects in the image include:
> 
> 1. **People**: There are three individuals in the image. 
>    - **Person in the Front**: This person is standing and appears to be holding a large bowl or container. The person is wearing a long, dark-colored garment, possibly a skirt or a long coat.
>    - **Person Behind the Person in the Front**: This person is standing behind the person in the front. They are wearing a light-colored garment, possibly a shirt or a jacket.
>    - **Person Behind the Person Behind the Person**: This

128 generated tokens; EOS: False; token ceiling: True; 6743.70 ms.

**florence**

> A painting of people standing around a table. There are baskets on the table in front of them. There is a woman in a red dress standing next to the table.

37 generated tokens; 647.94 ms.

### scene_10 (ordinary)

Input SHA-256: `2fb7febc73bf3113266c6ff2a0fe21159efa440f6dee8c858b2c72ef6a375643`; dimensions: [1280, 1696].

Source: https://commons.wikimedia.org/wiki/File:Huntington_Dog_Beach_and_Bolsa_Chica.jpg

License: CC BY-SA 4.0

**smolvlm**

> An aerial shot of the Netherlands. The river IJsselmeer is on the left side of the image, and the IJsselmeer is on the right side. The IJsselmeer is a large river that flows from the North Sea to the South Sea. The Netherlands is a country in Western Europe. The Netherlands is known for its canals. The canals are a major feature of the Netherlands. The Netherlands is a country that is known for its architecture. The architecture is a mix of Dutch and European styles.

111 generated tokens; EOS: True; token ceiling: False; 5299.93 ms.

**florence**

> This is an aerial view of a city. The sky is blue with white fluffy clouds. The water is blue and calm. The land is brown. There are many buildings and houses on the land.

42 generated tokens; 663.77 ms.

### scene_11 (ordinary)

Input SHA-256: `3dae75e7e6274c66ed235f4cc675dd71c949d3d198debd24c8628984daa7ec7d`; dimensions: [1280, 852].

Source: https://commons.wikimedia.org/wiki/File:Jesen%C3%ADk_train_station_2025.01.jpg

License: CC BY-SA 4.0

**smolvlm**

> A train station with two trains parked facing away from the viewer. The train on the right is a blue train with a red sign on top of it. The train on the left is a white train with a blue stripe along the side. There is a pole in the foreground with a sign on it that says "1". There is snow on the ground. The sky is dark with a thick, dark cloud above the station.

87 generated tokens; EOS: True; token ceiling: False; 4192.09 ms.

**florence**

> Two blue and white trains are parked at a train station at night. There is a light pole in front of the platform with a sign on it.

33 generated tokens; 641.74 ms.

## SmolVLM token-ceiling extension

Only the five original truncated captions were rerun at 256 tokens; all five still lacked EOS. No other model, completed caption or warmup was rerun.

### scene_01 (256 tokens)

**Extended SmolVLM**

> The image depicts a large, ornate, and colorful deity, likely a Hindu goddess, prominently featured in the center of the image. The deity is seated on a throne, with its arms outstretched, and is surrounded by a large, swirling, and billowing cloud of smoke. The goddess is adorned with elaborate jewelry, including a large, ornate headdress, and a richly decorated skirt. Her body is adorned with multiple arms, each holding a different object, which may represent various aspects of the goddess's power or attributes.
> 
> The goddess is surrounded by a group of people, some of whom are holding objects, likely offerings or incense sticks, in their hands. These objects are placed on a platform or a large, flat surface, which may be a stage or a platform for the goddess's worship. The people are dressed in traditional Indian attire, which includes long, colorful saris.
> 
> In the background, there are trees and what appears to be a building or a structure, suggesting that the scene is taking place in a temple or a sacred site. The sky is partially visible, with some clouds, indicating that the scene is likely taking place during a religious or cultural event.
> 
> The image conveys a sense of reverence and devotion, as the people

256 generated tokens; EOS: False; token ceiling: True; 12252.89 ms.

### scene_05 (256 tokens)

**Extended SmolVLM**

> The image depicts a vibrant and colorful table setup, likely intended for a festive or celebratory occasion. The table is covered with a yellow tablecloth, which is complemented by a colorful patterned drape that includes shades of purple, yellow, and red. The table is also adorned with various fruits and vegetables, arranged in a visually appealing manner.
> 
> Starting from the top, there is a framed photograph of a person, likely a family member or close friend, positioned in the center of the table. The photograph is bordered by a decorative frame, adding a touch of elegance to the setup. Below the photograph, there is a bowl filled with fresh apples, which are likely part of the fruit selection.
> 
> To the left of the bowl, there is a basket containing a variety of fruits, including bananas, apples, and possibly other types of produce. The bananas are prominently displayed, and they are accompanied by a small bowl filled with a green leafy vegetable, possibly a type of lettuce or spinach.
> 
> To the right of the bowl, there is a bowl filled with a variety of fruits, including bananas, apples, and possibly other types of produce. The bowl is also adorned with a decorative element, possibly a flower or a small plant, adding a touch of nature to

256 generated tokens; EOS: False; token ceiling: True; 12241.53 ms.

### scene_07 (256 tokens)

**Extended SmolVLM**

> The image depicts a cozy, rustic interior of a traditional house. The room is dimly lit, with a warm orange hue, suggesting that it is either early morning or late afternoon. The walls are made of rough-hewn stone, giving the space a rustic and homely feel. The ceiling is made of wooden beams, adding to the rustic charm of the room.
> 
> In the center of the room, there is a small, round, glowing fire pit. The fire pit is surrounded by a few items: a few metal pots and pans, a small bowl, and a few other objects that appear to be cooking utensils. The fire is small, and it is not actively burning, indicating that it is not the primary source of heat for the room.
> 
> To the right of the fire pit, there is a woman seated on a raised platform. She is wearing a traditional outfit, which includes a long, loose-fitting garment with a patterned design and a headscarf. The woman is engaged in a ritual or activity, possibly cooking or preparing food. She is holding a long, thin cooking utensil, which appears to be a ladle or a spoon, and is stirring or stirring something in a pot or pan.
> 
> The room is furnished

256 generated tokens; EOS: False; token ceiling: True; 11805.94 ms.

### scene_08 (256 tokens)

**Extended SmolVLM**

> In an outdoor setting, a group of young men are playing soccer on a stone-paved area. One of the players is in a blue shirt with the number 38 on the back. The player is stretching out his body with one arm extended towards the ball. Another player is in a white shirt with a blue and black graphic on the back. The player in the white shirt is looking at the player in the blue shirt. The player in the blue shirt is looking at the ball. The player in the white shirt has his arms extended out to the sides. The player in the blue shirt has his arms extended out to the sides. The player in the white shirt has his arms extended out to the sides. The player in the blue shirt has his arms extended out to the sides. The player in the white shirt has his arms extended out to the sides. The player in the blue shirt has his arms extended out to the sides. The player in the white shirt has his arms extended out to the sides. The player in the blue shirt has his arms extended out to the sides. The player in the white shirt has his arms extended out to the sides. The player in the blue shirt has his arms extended out to the sides. The player in the white shirt

256 generated tokens; EOS: False; token ceiling: True; 11638.34 ms.

### scene_09 (256 tokens)

**Extended SmolVLM**

> The image depicts a scene of a kitchen or cooking area. The primary objects in the image include:
> 
> 1. **People**: There are three individuals in the image. 
>    - **Person in the Front**: This person is standing and appears to be holding a large bowl or container. The person is wearing a long, dark-colored garment, possibly a skirt or a long coat.
>    - **Person Behind the Person in the Front**: This person is standing behind the person in the front. They are wearing a light-colored garment, possibly a shirt or a jacket.
>    - **Person Behind the Person Behind the Person**: This person is standing behind the person in the back. They are wearing a dark-colored garment, possibly a coat or a sweater.
> 
> 2. **Cooking Area**:
>    - **Table**: In the foreground, there is a table with various items on it. The table is covered with a white cloth.
>    - **Baskets**: There are two baskets on the table. One basket is filled with food items, possibly bread or other types of bread. The other basket is empty.
>    - **Cooking Tools**: There are some cooking tools on the table, including a large knife and a bowl.
> 
> 3. **

256 generated tokens; EOS: False; token ceiling: True; 11774.36 ms.

## Concise grounded prompt experiment

Only instruction text changed; the same eleven images used 128 tokens and one beam, with no warmup.

> Describe the main subject, activity, important visible objects, and their relationships in at most four short sentences. Prioritize details essential to understanding the scene. Avoid repetition, speculation, and unsupported cultural identities. Do not describe minor background details unless they are important.

EOS complete: 6/11; median inference: 4926.70 ms; peak CUDA: 1124.16 MiB.

### scene_01 (concise prompt)

**Concise SmolVLM**

> The image depicts a large, ornate deity with multiple arms, prominently featuring the goddess Durga. The goddess is seated on a throne and is surrounded by a large, swirling cloud of smoke. Her body is adorned with intricate patterns and jewelry, including a large, ornate headdress with multiple arms. The goddess is surrounded by a crowd of people, some of whom are holding objects resembling incense sticks, which are likely offerings to the goddess. The people are dressed in traditional Indian attire, and they are all smiling and appear to be in a festive mood.
> 
> The background includes a building with a large, white wall and a few trees

128 generated tokens; EOS: False; token ceiling: True; 6714.84 ms.

### scene_02 (concise prompt)

**Concise SmolVLM**

> In this image, there are a lot of small lights arranged on the floor. There are some coins placed on the floor.

26 generated tokens; EOS: True; token ceiling: False; 1499.96 ms.

### scene_03 (concise prompt)

**Concise SmolVLM**

> The image depicts a street scene featuring a large, colorful lion costume being worn by a performer. The costume is predominantly yellow with red accents, featuring intricate patterns and designs. The lion's face is prominently featured, with large, expressive eyes and a wide, open mouth that reveals a series of sharp teeth. The costume also includes a mane that is adorned with additional red and yellow patterns.
> 
> The performer is dressed in yellow pants and red shoes, which are typical of lion dance costumes. The performer is holding a long, thin stick in their right hand, which is likely used to control the lion's movements. The background of the

128 generated tokens; EOS: False; token ceiling: True; 5812.02 ms.

### scene_04 (concise prompt)

**Concise SmolVLM**

> A woman kneeling on a table in front of a tea set with an umbrella.

18 generated tokens; EOS: True; token ceiling: False; 1237.48 ms.

### scene_05 (concise prompt)

**Concise SmolVLM**

> The image features a vibrant and colorful table setup, adorned with various fruits and vegetables. At the center of the table is a framed photo of a person, likely a family or a significant figure, adding a personal touch to the arrangement. Surrounding the photo are an assortment of fruits, including bananas, apples, and pomegranates, all neatly arranged in a visually appealing manner.
> 
> On the table, there are also several bowls and baskets filled with fresh produce, including tomatoes, cucumbers, and leafy greens. These items are arranged in a way that suggests a variety of fresh produce, indicating a focus on healthy eating.
> 
> In the background

128 generated tokens; EOS: False; token ceiling: True; 6133.02 ms.

### scene_06 (concise prompt)

**Concise SmolVLM**

> A bicycle is leaning against a set of black doors. The doors are framed with white trim and have graffiti on them. The graffiti is in various colors including blue, white, yellow, and black. The bicycle is black and has a front basket. The sidewalk is made of brick and is lined with black doors.

64 generated tokens; EOS: True; token ceiling: False; 3117.29 ms.

### scene_07 (concise prompt)

**Concise SmolVLM**

> The image depicts a cozy, traditional living space. The room is constructed with earthy tones, primarily red, orange, and brown, giving it a warm and inviting atmosphere. The walls are made of rough-hewn stones, and the ceiling is constructed from wooden beams. The room features a thatched roof, which adds to the rustic charm of the space.
> 
> In the center of the room, there is a small, round, glowing fire pit. The fire pit is surrounded by a mat, and a few items are placed around it, including a bowl, a ladle, and a few other cooking utensils. The fire is

128 generated tokens; EOS: False; token ceiling: True; 6220.57 ms.

### scene_08 (concise prompt)

**Concise SmolVLM**

> In an outdoor setting, a group of young men are playing soccer. One of them is wearing a blue shirt with the number 38 on the back. The other players are in various poses, some stretching, others running. In the background, there is a brick wall and several other people standing and walking.

64 generated tokens; EOS: True; token ceiling: False; 3148.57 ms.

### scene_09 (concise prompt)

**Concise SmolVLM**

> A painting of a kitchen scene. There are three women in the kitchen. One woman is holding a bowl.

23 generated tokens; EOS: True; token ceiling: False; 1407.29 ms.

### scene_10 (concise prompt)

**Concise SmolVLM**

> An aerial shot of the Netherlands, showing the IJ (the most important river in the country) and the IJsselmeer (the second most important river). The IJ is a narrow strip of water between the Netherlands and Belgium. The IJsselmeer is a large river that flows through the center of the country. The Netherlands is a country in Europe, and the IJsselmeer is a major river in the country.

95 generated tokens; EOS: True; token ceiling: False; 4926.70 ms.

### scene_11 (concise prompt)

**Concise SmolVLM**

> The scene depicts a snowy train station at night. The station is equipped with a red light, indicating that it is operational. The ground is covered in snow, and the tracks are empty. There are two trains parked at the station, both of which are blue. The train on the left is a double-decker, while the one on the right is a single-decker. Both trains have their headlights on, suggesting that they are either at a stop or in motion.
> 
> Above the station, the sky is dark, and there are clouds, which are typical for a night scene. The lighting is sufficient to illuminate

128 generated tokens; EOS: False; token ceiling: True; 6137.16 ms.

## Florence task and region diagnostics

### Caption task variants

**<CAPTION>**

> A group of women dressed in traditional Indian garb.

13 generated tokens; token ceiling: False; 2366.15 ms.

**<DETAILED_CAPTION>**

> In this image we can see a few people, among them some are holding objects, there is a tree, there are some wires, also we can the sky.

35 generated tokens; token ceiling: False; 643.17 ms.

**<MORE_DETAILED_CAPTION>**

> A group of women are dancing together. They are all dressed in traditional Indian garb. One of the women is in the middle of the group dancing. She is wearing a colorful garb and headdress. The women are holding brown bowls in their hands. There is smoke coming out of the bowls. There are wires hanging above the women.

71 generated tokens; token ceiling: False; 1172.93 ms.

### Manual crop

Crop bounds: `[300, 100, 700, 600]`.

**Full image**

> A group of women are dancing together. They are all dressed in traditional Indian garb. One of the women is in the middle of the group dancing. She is wearing a colorful garb and headdress. The women are holding brown bowls in their hands. There is smoke coming out of the bowls. There are wires hanging above the women.

71 generated tokens; 3334.07 ms.

**Manual crop**

> Three women are standing in front of a picture of a woman dressed in traditional Indian garb. The woman on the right is wearing a red saree with a gold necklace and earrings. She is holding a brown bowl in each of her hands. Her face is painted with red and white paint. Her hair is pulled back in a ponytail. Behind the women on the left is another woman wearing a saree. Behind them is a large statue of lord Ganesha. The statue is surrounded by white smoke.

106 generated tokens; 1449.54 ms.

### Independent grid views

**full [0, 0, 980, 692]**

> A group of women are dancing together. They are all dressed in traditional Indian garb. One of the women is in the middle of the group dancing. She is wearing a colorful garb and headdress. The women are holding brown bowls in their hands. There is smoke coming out of the bowls. There are wires hanging above the women.

71 generated tokens; token ceiling: False; 2584.80 ms.

**top_left [0, 0, 490, 346]**

> This is an image of a city. The city has tall buildings. The buildings are gray. The sky is white. There are black wires in the sky. The wires are long and thin. There is smoke coming out of the wires. The smoke is gray and white. The people are holding brown pots in their hands. The pots are large and brown.

74 generated tokens; token ceiling: False; 1152.05 ms.

**top_right [490, 0, 980, 346]**

> This is an image of a woman. The woman has a large headdress on. The headdress is red and gold. There is a tree to the right of the woman with green leaves. The tree is tall and green. There are brown pots on the ground in front of the women. The women has long black hair. The sky is white and cloudy.

75 generated tokens; token ceiling: False; 1213.46 ms.

**bottom_left [0, 346, 490, 692]**

> There are three women standing together. They are all wearing red sarees. The woman on the left is wearing a white saree with a gold embroidery on it. She is also wearing a gold necklace and gold earrings. The two women on the right are holding up a bowl. The bowl is brown in color. One of the women is smiling. There is a man in the background.

83 generated tokens; token ceiling: False; 1195.44 ms.

**bottom_right [490, 346, 980, 692]**

> A woman is wearing a red and white saree. She has a gold necklace around her neck. There is a woman standing behind her wearing a white and red saree with a white cloth draped over her shoulders.

46 generated tokens; token ceiling: False; 766.45 ms.

### Native dense region output

Validated boxes: 6; generated tokens: 28; EOS: True.

```json
[
  {
    "region_id": 1,
    "bbox": [
      77.91000366210938,
      366.4139709472656,
      132.79000854492188,
      438.3819885253906
    ],
    "description": "human face",
    "valid": true,
    "validation_errors": []
  },
  {
    "region_id": 2,
    "bbox": [
      236.6699981689453,
      396.8619689941406,
      290.57000732421875,
      463.2939758300781
    ],
    "description": "human face",
    "valid": true,
    "validation_errors": []
  },
  {
    "region_id": 3,
    "bbox": [
      384.6499938964844,
      414.1619873046875,
      431.69000244140625,
      481.97796630859375
    ],
    "description": "human face",
    "valid": true,
    "validation_errors": []
  },
  {
    "region_id": 4,
    "bbox": [
      545.3699951171875,
      399.6299743652344,
      587.510009765625,
      467.44598388671875
    ],
    "description": "human face",
    "valid": true,
    "validation_errors": []
  },
  {
    "region_id": 5,
    "bbox": [
      616.9100341796875,
      133.20999145507812,
      662.9700317382812,
      189.26199340820312
    ],
    "description": "human face",
    "valid": true,
    "validation_errors": []
  },
  {
    "region_id": 6,
    "bbox": [
      178.85000610351562,
      432.15399169921875,
      217.07000732421875,
      480.593994140625
    ],
    "description": "human face",
    "valid": true,
    "validation_errors": []
  }
]
```

Raw native generation:

```text
</s><s>human face<loc_79><loc_529><loc_135><loc_633><loc_241><loc_573><loc_296><loc_669><loc_392><loc_598><loc_440><loc_696><loc_556><loc_577><loc_599><loc_675><loc_629><loc_192><loc_676><loc_273><loc_182><loc_624><loc_221><loc_694></s>
```

## Sanity image outputs

**smolvlm**

> Two tabby cats are sleeping on a pink blanket. One cat is curled up with its head on the other cat's back.

28 generated tokens; EOS: True; token ceiling: False; 2365.95 ms.

**florence**

> There are two cats laying on a pink blanket. There are remotes next to the cats. The cats are brown and black.

29 generated tokens; 1864.92 ms.

## Raw evidence archive

Exact original files, images, blank review sheets and retired experiment code are preserved locally under [.local_archive/smolvlm_commitment_20261108/](../.local_archive/smolvlm_commitment_20261108/). The archive is ignored by Git; this consolidated report and the insights report are versionable.

The archive manifest maps original paths to archived paths with SHA-256 checksums. Historical paths inside the original records are intentionally unchanged; resolve them using that manifest. Previous cleanup archives remain intact.
