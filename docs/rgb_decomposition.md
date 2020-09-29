RGB Decomposition
=================

RGB products generated with HyP3 use both co-pol (VV or HH) and cross-pol (VH or HV) backscatter values to generate a color image from SAR data. This approach facilitates visual interpretation by decomposing the signals into surface scattering with some volume scattering (red band), volume scattering (green band), and surface scattering with very low volume scattering (blue band).

The dual-pol SAR dataset first undergoes radiometric terrain correction (RTC) to adjust for the distortions present in the images due to the side-looking geometry of SAR data acquisition. The RTC images are output in power scale, and any pixels with values less than -48 dB are set to 0. The RGB values are calculated using a combination of the co-pol (CP) and cross-pol (XP) pixel values. The output RGB GeoTIFF is scaled so that the values for each band range from 1 to 255. Zero values are reserved for pixels with no data.

### Interpreting the Images

Calm water generally has very low returns in all polarizations, and areas with very low backscatter will appear blue. Desert landscapes have a backscatter signature similar to that of water, however, so care should be taken in interpretation of the blue color based on the location.

The green band is determined by the magnitude of the cross-pol returns, which indicates the extent of volume scattering. One of the most common volume scatterers is vegetation, and areas with high cross-pol returns appear more green in the decomposition. There are other volume scatterers, such as glacial ice; areas where the volume to surface scattering ratio is larger than expected for vegetation will display in teal.

The red channel is used to indicate areas that are neither water nor vegetation. Urban areas and other locations with relatively low levels of volume scattering, but higher surface scatter returns than water, will appear more red in this decomposition.

### Decomposition Calculations

Note that dual-pol image acquisition may provide either VV/VH returns or HH/HV returns, depending on the sensor mode. The same decomposition approach can be applied to either mode; use the co-pol (S<sub>CP</sub>) and cross-pol (S<sub>XP</sub>) pixel values available for the specific dataset. Calculations are applied on a pixel-by-pixel basis.

First, a spatial mask is generated using a threshold (*k*) applied to the S<sub>XP</sub> data so that pixels with values above the threshold are included in the red and green channel mask (M<sub>R</sub>) and those below the threshold are included in the blue band mask (M<sub>B</sub>). Threshold values typically range between -22 and -25 dB, and the default for HyP3 processing is -24 dB.

M<sub>B</sub> = S<sub>XP</sub> < *k*

M<sub>R</sub> = S<sub>XP</sub> >= *k*

Pixels with invalid crosspol data will also be masked out (M<sub>X</sub>):

M<sub>X</sub> = S<sub>XP</sub> > 0

In all three cases (M<sub>B</sub>, M<sub>R</sub>, M<sub>X</sub>), the mask pixels are assigned values of 1 for true and 0 for false. 

The surface scattering (P<sub>s</sub>) component of the data is calculated as follows:

P<sub>s</sub> = S<sub>CP</sub> - 3 S<sub>XP</sub>

and is oppositely applied to the red and blue bands:

P<sub>R</sub> = P<sub>s</sub>

P<sub>B</sub> = -P<sub>s</sub>

Any negative P<sub>R</sub> or P<sub>B</sub> values should be set to zero.

The difference between the co- and cross-pol values (S<sub>d</sub>) is calculated: 

S<sub>d</sub> = (S<sub>CP</sub> -  S<sub>XP</sub>)

Any negative S<sub>d</sub> values should be set to zero.

Finally, the spatial masks and specific scalars are applied to the intensity values to appropriately stretch the dynamic range of each band from 1 to 255:

z = 2 / 𝜋 M<sub>B</sub> arctan(S<sub>d</sub> <sup>0.5</sup>)

a<sub>R</sub> = 254 M<sub>X</sub> (2 M<sub>R</sub> (P<sub>R</sub>) <sup>0.5</sup> + z) + 1

a<sub>G</sub> = 254 M<sub>X</sub> (3 M<sub>R</sub> (S<sub>XP</sub>) <sup>0.5</sup> + 2z) + 1

a<sub>B</sub> = 254 M<sub>X</sub> (2 (P<sub>B</sub>) <sup>0.5</sup> + 5z) + 1

Any values greater than 255 in any of the bands (a<sub>R</sub>, a<sub>G</sub>, a<sub>B</sub>) are set to 255, then the a<sub>RGB</sub> bands are combined to generate an RGB image in 8-bit unsigned integer format.
