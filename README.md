# CMU AI-SDM + Meta Repository

## Project Structure

* [Data_Loading_Meta.qmd](https://github.com/jaylouissaint/AISDM_Meta/blob/main/Data_Loading_Meta.qmd) - Script for cleaning data
* [Situation Report](https://github.com/jaylouissaint/AISDM_Meta/tree/main/Situation%20Report) - A modified situation report for Winter Storm Fern
* [Interactive Version](https://github.com/jaylouissaint/AISDM_Meta/tree/main/Interactive%20Version) - An interactive streamlit version of the above situation report for Winter Storm Fern
* [SAM Attempt](https://github.com/jaylouissaint/AISDM_Meta/tree/main/SAM%20Attempt) - Initial attempts at incorporating Meta's SAM model for disaster management
* [Previous Work](https://github.com/jaylouissaint/AISDM_Meta/tree/main/Previous%20Work) - Previous iterations of the situation report

## Data_Loading_Meta.qmd

This script is used to clean and aggregate Meta’s Data for Good crisis datasets. It is utilized by various subsequent parts of the project, including the situation report and interactive app.

## Situation Report

We have developed a situation report for Winter Storm Fern. The structure is based on the [CrisisReady Situation Report for LA Fires](https://www.crisisready.io/resources/situation-reports/). The situation report utilizes Meta’s Data for Good crisis datasets, which are limited-assess datasets that track population changes through Facebook with a focus on Tennessee, Kentucky and surrounding states, and county-level demographic data from the American Community Survey in 2022. There is also an **abridged version** that is intended for uses by disaster managers.

## Interactive Version

We have also developed a digital version of the situation report using Streamlit. This app allows for interactive maps and customizable plots that can be filtered for specific counties and/or time zones. This app utilizes the same datasets as the situation report: Meta’s Data for Good crisis datasets, which are limited-assess datasets that track population changes through Facebook with a focus on Tennessee, Kentucky and surrounding states, and county-level demographic data from the American Community Survey in 2022.

## SAM Attempt

We are in the process of developing a workflow that utilizes [Meta's SAM model](https://ai.meta.com/research/sam3/), possibly in conjunction with Meta’s Data for Good crisis datasets. The most up-to-date information can be found in the [README](https://github.com/jaylouissaint/AISDM_Meta/blob/main/SAM%20Attempt/README.md) for this folder.

## Previous Work

All previous iterations of the situation report can be found here. They demonstrate our developments from the original [CrisisReady sitation report](https://www.crisisready.io/resources/situation-reports/) to our modified version.
