import { each, filter, map, min, max, sortBy, toString } from "lodash";
import React, { useMemo, useState, useEffect } from "react";
import resizeObserver from "@/services/resizeObserver";
import { RendererPropTypes } from "@/visualizations/prop-types";
import echarts from "@/visualizations/shared/echarts/register";
import { createChartInstance, getThemePalette } from "@/visualizations/shared/echarts/createChartInstance";
import ColorPalette from "@/visualizations/ColorPalette";
import "echarts-wordcloud";

import "./renderer.less";

function computeWordFrequencies(rows: any, column: any) {
  const result: Record<string, number> = {};
  each(rows, row => {
    const wordsList = toString(row[column]).split(/\s/g);
    each(wordsList, d => {
      result[d] = (result[d] || 0) + 1;
    });
  });
  return result;
}

function getWordsWithFrequencies(rows: any, wordColumn: any, frequencyColumn: any) {
  const result: Record<string, number> = {};
  each(rows, row => {
    const count = parseFloat(row[frequencyColumn]);
    if (Number.isFinite(count) && count > 0) {
      const word = toString(row[wordColumn]);
      result[word] = count;
    }
  });
  return result;
}

function applyLimitsToWords(words: any[], { wordLength, wordCount }: any) {
  wordLength.min = Number.isFinite(wordLength.min) ? wordLength.min : null;
  wordLength.max = Number.isFinite(wordLength.max) ? wordLength.max : null;
  wordCount.min = Number.isFinite(wordCount.min) ? wordCount.min : null;
  wordCount.max = Number.isFinite(wordCount.max) ? wordCount.max : null;

  return filter(words, ({ text, count }) => {
    const wordLengthFits =
      (!wordLength.min || text.length >= wordLength.min) && (!wordLength.max || text.length <= wordLength.max);
    const wordCountFits = (!wordCount.min || count >= wordCount.min) && (!wordCount.max || count <= wordCount.max);
    return wordLengthFits && wordCountFits;
  });
}

function prepareWords(rows: any, options: any) {
  let result: { text: string; count: number }[] = [];

  if (options.column) {
    let freqMap: Record<string, number>;
    if (options.frequenciesColumn) {
      freqMap = getWordsWithFrequencies(rows, options.column, options.frequenciesColumn);
    } else {
      freqMap = computeWordFrequencies(rows, options.column);
    }
    result = sortBy(
      map(freqMap, (count, text) => ({ text, count })),
      [({ count }) => -count, ({ text }) => -text.length]
    );
  }

  const counts = map(result, item => item.count);
  const minCount = min(counts) ?? 1;
  const maxCount = max(counts) ?? 1;
  const palette = Object.values(ColorPalette).filter(v => typeof v === "string") as string[];

  return applyLimitsToWords(
    map(result, (item, index) => ({
      name: item.text,
      value: item.count,
      textStyle: {
        color: palette[index % palette.length],
      },
    })),
    { wordLength: options.wordLengthLimit, wordCount: options.wordCountLimit }
  ).map(w => ({
    ...w,
    textStyle: {
      ...w.textStyle,
      fontSize: 10 + ((w.value - minCount) / (maxCount - minCount || 1)) * 50,
    },
  }));
}

export default function Renderer({ data, options }: any) {
  const [container, setContainer] = useState<HTMLDivElement | null>(null);
  const words = useMemo(() => prepareWords(data.rows, options), [data, options]);

  useEffect(() => {
    if (!container || words.length === 0) {
      return;
    }

    const palette = getThemePalette();
    const { destroy } = createChartInstance(container, {
      series: [
        {
          type: "wordCloud",
          shape: "circle",
          left: "center",
          top: "center",
          width: "95%",
          height: "95%",
          sizeRange: [12, 60],
          rotationRange: [0, 0],
          gridSize: 8,
          drawOutOfBound: false,
          textStyle: {
            fontFamily: palette.fontFamily,
            color: () => palette.text,
          },
          emphasis: {
            textStyle: { color: palette.brand },
          },
          data: words,
        },
      ],
    });

    const unwatch = resizeObserver(container, () => {
      echarts.getInstanceByDom(container)?.resize();
    });

    return () => {
      unwatch();
      destroy();
    };
  }, [container, words]);

  return <div className="word-cloud-visualization-container" ref={setContainer} />;
}

Renderer.propTypes = RendererPropTypes;
